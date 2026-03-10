// JavaScript = The programming language of the web
// This file makes the page interactive

// Console.log prints messages to the browser console (F12 to see it)
console.log("Hello! Your JavaScript is working!");

// Get elements from the HTML
// document.querySelector finds the first element with that class
const buttons = document.querySelectorAll('.btn');  // Get all buttons
const skillCards = document.querySelectorAll('.skill-card');  // Get all skill cards

// Add click event to all buttons
buttons.forEach(button => {
    // addEventListener listens for events (like 'click')
    button.addEventListener('click', function() {
        // This code runs when button is clicked
        alert('Button clicked! You can link this to a real project later.');
        console.log("A button was clicked!");
    });
});

// Add counter to skill cards
let clickCount = 0;  // Variable to store number

skillCards.forEach(card => {
    card.addEventListener('click', function() {
        // Increment (increase by 1)
        clickCount++;

        // Change the card's background color
        this.style.background = '#667eea';
        this.style.color = 'white';

        // Log to console
        console.log(`Skill card clicked! Total clicks: ${clickCount}`);

        // Change it back after 1 second (1000 milliseconds)
        setTimeout(() => {
            this.style.background = '#f8f9fa';
            this.style.color = '#333';
        }, 1000);
    });
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();  // Stop the default jump behavior

        const targetId = this.getAttribute('href');
        const targetElement = document.querySelector(targetId);

        if (targetElement) {
            // Scroll smoothly to the element
            targetElement.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Log when page finishes loading
window.addEventListener('load', function() {
    console.log("Page fully loaded!");
    console.log("Open the console (F12) to see these messages");
});

// Example of a function
function greetUser(name) {
    return `Hello, ${name}! Welcome to my page.`;
}

// Call the function
console.log(greetUser("Beginner"));

// Example of an if/else statement
const hour = new Date().getHours();  // Get current hour (0-23)

if (hour < 12) {
    console.log("Good morning!");
} else if (hour < 18) {
    console.log("Good afternoon!");
} else {
    console.log("Good evening!");
}
