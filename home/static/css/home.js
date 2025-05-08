document.addEventListener("DOMContentLoaded", function () {
    // Smooth scrolling for sidebar links
    const navLinks = document.querySelectorAll(".sidebar a");
    navLinks.forEach(link => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const targetId = this.getAttribute("href").substring(1);
            const targetSection = document.getElementById(targetId);

            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: "smooth",
                    block: "start" // Makes sure it starts at the top
                });
            }
        });
    });

    // Fix login and signup buttons
    document.querySelectorAll('.login-btn, .signup-btn').forEach(button => {
        button.addEventListener('click', function (event) {
            event.stopPropagation(); // Prevents sidebar or other scripts from interfering
            window.location.href = this.getAttribute("href"); // Manually navigate
        });
    });
});
