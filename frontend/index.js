const user = {
    name: 'John Doe',
}

const sayHello = function() {
    console.log(`Hello, my name is ${this.name}`);
}

let newUser = {
    name: 'Jane Smith',
};

const user1 = sayHello.bind(newUser);


console.log('User object:', newUser);
user1();

console.log('User object:', user);
sayHello.bind(user)();