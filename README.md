
# 📄 PDF Page Finder

A simple desktop app that helps you find the exact page of a PDF book by uploading a small image snippet or screenshot of a paragraph. 

I built this project to learn more about desktop app design, image matching, and how to use AI tools effectively in a real-world coding workflow.

---

## How I Used AI to Build This

I wanted to be completely open about how this project was made. I used an AI assistant to help write the code, but I managed the logic, design, and testing myself.

* **What the AI did**: It helped me write the boilerplate code for the user interface (Tkinter), suggested using the `PyMuPDF` and `OpenCV` libraries, and showed me how to run the search on a separate thread so the app doesn't freeze.
* **What I did**: I came up with the project idea, decided how the app should flow, tested the features, and fixed bugs. For example, I had to fix an issue where the matched page image wouldn't show up properly on the screen because of how Python cleans up memory.

Using AI helped me build this much faster than if I had started completely from scratch, and it taught me a lot about how image matching works
