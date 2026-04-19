from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import pika

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RabbitMQBroker:
    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.rabbitmq_url
        self.exchange = settings.rabbitmq_exchange
        self.listener_queue = settings.rabbitmq_listener_queue
        self.internal_topic = settings.rabbitmq_internal_topic
        self.activity_topic = settings.rabbitmq_activity_topic
        self.reconnect_seconds = settings.rabbitmq_reconnect_seconds
        self.publish_enabled = settings.event_publish_enabled
        self.listener_enabled = settings.event_listener_enabled

        self._publish_lock = threading.Lock()
        self._publish_connection: pika.BlockingConnection | None = None
        self._publish_channel: pika.adapters.blocking_connection.BlockingChannel | None = None
        self._publish_blocked_until = 0.0

        self._listener_thread: threading.Thread | None = None
        self._listener_stop = threading.Event()

    def _new_connection(self) -> pika.BlockingConnection:
        params = pika.URLParameters(self.url)
        params.heartbeat = 30
        params.blocked_connection_timeout = 30
        params.connection_attempts = 1
        params.retry_delay = 0.2
        params.socket_timeout = 1
        params.stack_timeout = 2
        return pika.BlockingConnection(params)

    def _ensure_publish_channel(self) -> pika.adapters.blocking_connection.BlockingChannel:
        with self._publish_lock:
            if self._publish_connection and self._publish_connection.is_open and self._publish_channel and self._publish_channel.is_open:
                return self._publish_channel

            self._close_publish_connection()
            self._publish_connection = self._new_connection()
            self._publish_channel = self._publish_connection.channel()
            self._publish_channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
            return self._publish_channel

    def _close_publish_connection(self) -> None:
        if self._publish_channel and self._publish_channel.is_open:
            try:
                self._publish_channel.close()
            except Exception:
                pass
        if self._publish_connection and self._publish_connection.is_open:
            try:
                self._publish_connection.close()
            except Exception:
                pass
        self._publish_channel = None
        self._publish_connection = None

    def publish(self, routing_key: str, message: dict[str, Any]) -> None:
        if not self.publish_enabled:
            return
        if time.time() < self._publish_blocked_until:
            return

        try:
            channel = self._ensure_publish_channel()
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(message, default=str).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
            print(f"Published event: {routing_key} with payload: {message}")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to publish event: {routing_key} with payload: {message} error: {exc}")
            logger.warning("RabbitMQ publish failed for %s: %s", routing_key, exc)
            self._close_publish_connection()
            self._publish_blocked_until = time.time() + self.reconnect_seconds

    def start_listener(self) -> None:
        print("Starting RabbitMQ listener...")
        if not self.listener_enabled:
            logger.info("RabbitMQ listener disabled by configuration")
            return
        
        print("RabbitMQ listener enabled, starting thread...")

        if self._listener_thread and self._listener_thread.is_alive():
            return
        
        print("RabbitMQ listener thread not running, starting new thread...")

        self._listener_stop.clear()
        self._listener_thread = threading.Thread(target=self._listener_loop, daemon=True, name="rabbitmq-listener")
        self._listener_thread.start()

    def stop_listener(self) -> None:
        self._listener_stop.set()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=3)
        self._listener_thread = None
        self._close_publish_connection()

    def _open_listener_resources(
        self,
    ) -> tuple[pika.BlockingConnection, pika.adapters.blocking_connection.BlockingChannel]:
        connection = self._new_connection()
        channel = connection.channel()
        channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        channel.queue_declare(queue=self.listener_queue, durable=True)
        channel.queue_bind(queue=self.listener_queue, exchange=self.exchange, routing_key=self.internal_topic)
        channel.queue_bind(queue=self.listener_queue, exchange=self.exchange, routing_key=self.activity_topic)
        logger.info(
            "RabbitMQ listener connected; queue=%s topics=[%s,%s]",
            self.listener_queue,
            self.internal_topic,
            self.activity_topic,
        )
        print(f"RabbitMQ listener connected; queue={self.listener_queue} topics=[{self.internal_topic},{self.activity_topic}]")
        return connection, channel

    def _on_message(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method_frame: pika.spec.Basic.Deliver,
        _: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        try:
            payload = json.loads(body.decode("utf-8"))
            self._dispatch_event(method_frame.routing_key, payload)
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            print(
                f"[RabbitMQ Consumer] ACK topic={method_frame.routing_key} payload={payload}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to process message (%s): %s", method_frame.routing_key, exc)
            channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=False)
        print(f"Received event: {method_frame.routing_key} with payload: {body.decode('utf-8')}")

    def _run_consumer(self, connection: pika.BlockingConnection, channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
        channel.basic_qos(prefetch_count=20)
        consumer_tag = channel.basic_consume(
            queue=self.listener_queue,
            on_message_callback=self._on_message,
            auto_ack=False,
        )
        try:
            while not self._listener_stop.is_set() and connection.is_open:
                # Keeps network events flowing while allowing graceful stop checks.
                connection.process_data_events(time_limit=1)
        finally:
            print("Stopping RabbitMQ listener... Closing channel and connection.")
            if channel.is_open:
                channel.basic_cancel(consumer_tag=consumer_tag)

    @staticmethod
    def _close_listener_resources(
        connection: pika.BlockingConnection | None,
        channel: pika.adapters.blocking_connection.BlockingChannel | None,
    ) -> None:
        try:
            if channel and channel.is_open:
                channel.close()
        except Exception:
            pass
        try:
            if connection and connection.is_open:
                connection.close()
        except Exception:
            pass

    def _listener_loop(self) -> None:
        while not self._listener_stop.is_set():
            connection: pika.BlockingConnection | None = None
            channel: pika.adapters.blocking_connection.BlockingChannel | None = None
            try:
                connection, channel = self._open_listener_resources()
                self._run_consumer(connection, channel)
            except Exception as exc:  # noqa: BLE001
                logger.warning("RabbitMQ listener disconnected: %s", exc)
                time.sleep(self.reconnect_seconds)
            finally:
                self._close_listener_resources(connection, channel)

    def _dispatch_event(self, routing_key: str, payload: dict[str, Any]) -> None:
        if routing_key.startswith("activity."):
            self._handle_activity_event(routing_key, payload)
            return

        if routing_key.startswith("internal."):
            logger.info("Internal event received: %s payload=%s", routing_key, payload)
            return

        logger.info("Unhandled topic received: %s payload=%s", routing_key, payload)

    def _handle_activity_event(self, routing_key: str, payload: dict[str, Any]) -> None:
        # Simulates a dedicated activity-consumer microservice.
        logger.info("Activity event received: %s payload=%s", routing_key, payload)


_broker_instance: RabbitMQBroker | None = None
_broker_lock = threading.Lock()


def get_event_broker() -> RabbitMQBroker:
    global _broker_instance
    if _broker_instance is not None:
        return _broker_instance

    with _broker_lock:
        if _broker_instance is None:
            _broker_instance = RabbitMQBroker()
        return _broker_instance
