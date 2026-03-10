# My First Webpage - Learning Project

This is your first coding project! It's a simple personal webpage built with HTML, CSS, and JavaScript.

## How to Open This Project

1. Navigate to the `beginner-project` folder
2. Double-click `index.html` to open it in your browser
3. That's it! No installation needed.

## What You'll Learn

### HTML (index.html)
- Structure of a webpage
- Semantic HTML tags (`<header>`, `<section>`, `<footer>`)
- How to organize content
- Links and buttons

### CSS (style.css)
- How to style elements
- Colors, fonts, and spacing
- Layout with Flexbox and Grid
- Hover effects and transitions
- Responsive design for mobile

### JavaScript (script.js)
- Variables and functions
- Event listeners (responding to clicks)
- DOM manipulation (changing the page)
- Console.log for debugging
- Conditional statements (if/else)

## Step-by-Step Guide

### 1. Understanding HTML

Open `index.html` and read the comments (text between `<!--` and `-->`).

**Key Concepts:**
- Tags come in pairs: `<h1>Text</h1>`
- Classes are for styling: `class="name"`
- The page has sections: header, about, skills, projects, contact, footer

**Try This:**
- Change "Your Name Here" to your actual name
- Change the tagline to describe yourself
- Add a new skill card by copying and pasting an existing one

### 2. Understanding CSS

Open `style.css` and read the comments (text between `/*` and `*/`).

**Key Concepts:**
- Selectors target HTML elements: `.header` targets `class="header"`
- Properties change how things look: `color: blue;`
- Every property ends with a semicolon `;`

**Try This:**
- Change the background gradient colors (line 12)
- Change the purple color `#667eea` to another color:
  - Red: `#ff0000`
  - Blue: `#0000ff`
  - Green: `#00ff00`
  - Orange: `#ff6600`
- Change the font size of `.name` to make it bigger or smaller
- Modify the hover effect on `.skill-card:hover`

### 3. Understanding JavaScript

Open `script.js` and read the comments (text after `//`).

**Key Concepts:**
- Variables store data: `let name = "John"`
- Functions are reusable code blocks
- Event listeners respond to user actions
- Console.log helps you debug

**Try This:**
- Open the browser console (Press F12, then click "Console" tab)
- See the messages logged by JavaScript
- Click on skill cards and watch them change color
- Click the "View Project" button
- Modify the alert message (line 14)

## Exercises to Practice

### Easy:
1. Change all colors from purple to your favorite color
2. Add your real social media links
3. Add a new section about your hobbies
4. Change the emojis in the skill icons

### Medium:
5. Add a 4th skill card (maybe React or Python?)
6. Change the gradient to use 3 colors instead of 2
7. Add a profile picture using `<img>` tag
8. Make the footer have a different background color

### Challenge:
9. Add a form where people can leave messages
10. Create a dark mode toggle button
11. Add more animations when you scroll
12. Create a navigation menu that jumps to sections

## Understanding the Code

### How CSS Grid Works
```css
.skills-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}
```
- `display: grid` - Use grid layout
- `repeat(3, 1fr)` - Create 3 equal columns
- `gap: 20px` - Space between items

### How Hover Effects Work
```css
.skill-card:hover {
    transform: translateY(-10px);
}
```
- `:hover` - When mouse is over element
- `transform` - Change position/size
- `translateY(-10px)` - Move up 10 pixels

### How JavaScript Events Work
```javascript
button.addEventListener('click', function() {
    alert('Button clicked!');
});
```
- `addEventListener` - Listen for an event
- `'click'` - The type of event
- `function() { }` - Code to run when event happens

## Next Steps

Once you understand this project:

1. **Customize It** - Make it truly yours
2. **Break It** - Try changing things and see what happens
3. **Fix It** - Learn to debug by breaking and fixing
4. **Experiment** - Add features you think would be cool

## Common Mistakes to Avoid

1. Forgetting semicolons `;` in CSS
2. Misspelling class names
3. Not closing tags: `<div>` needs `</div>`
4. Forgetting quotes: `class="name"` not `class=name`
5. Case sensitivity: `.Name` is different from `.name`

## Debugging Tips

**If something doesn't work:**

1. **Check the Console (F12)**
   - Look for red error messages
   - They tell you exactly what's wrong

2. **Validate Your HTML**
   - Make sure all tags are closed
   - Check for typos in class names

3. **Check CSS Syntax**
   - Each property needs a `:` and `;`
   - Brackets must match: `{` and `}`

4. **Use Console.log**
   ```javascript
   console.log("Does this code run?");
   console.log(variableName);
   ```

## Resources for Learning More

- **HTML**: https://developer.mozilla.org/en-US/docs/Web/HTML
- **CSS**: https://developer.mozilla.org/en-US/docs/Web/CSS
- **JavaScript**: https://javascript.info/

## Questions to Test Your Understanding

1. What's the difference between `<div>` and `<section>`?
2. How do you center text in CSS?
3. What does `addEventListener` do?
4. What's the difference between `class` and `id`?
5. How do you change an element's color with JavaScript?

Try to answer these, then check the code to verify!

## Your Next Project

After mastering this, try building:
- A photo gallery
- A simple calculator
- A weather app (using an API)
- A todo list

Good luck and happy coding! 🚀
