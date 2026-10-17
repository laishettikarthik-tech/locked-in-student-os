document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm], form.delete-form[data-confirm]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!window.confirm(form.dataset.confirm || "Are you sure?")) event.preventDefault();
    });
  });

  const display = document.getElementById("timer-display");
  if (display) {
    let initialMinutes = 25;
    let remaining = initialMinutes * 60;
    let interval = null;
    let running = false;
    const startButton = document.getElementById("timer-start");
    const resetButton = document.getElementById("timer-reset");
    const render = () => {
      const m = Math.floor(remaining / 60).toString().padStart(2, "0");
      const s = (remaining % 60).toString().padStart(2, "0");
      display.textContent = `${m}:${s}`;
    };
    document.querySelectorAll(".preset").forEach(button => {
      button.addEventListener("click", () => {
        if (interval) clearInterval(interval);
        interval = null;
        running = false;
        initialMinutes = Number(button.dataset.minutes) || 25;
        remaining = initialMinutes * 60;
        startButton.textContent = "Start";
        document.querySelectorAll(".preset").forEach(p => p.classList.remove("active"));
        button.classList.add("active");
        render();
      });
    });
    startButton.addEventListener("click", () => {
      if (running) {
        clearInterval(interval);
        interval = null;
        running = false;
        startButton.textContent = "Resume";
      } else {
        running = true;
        startButton.textContent = "Pause";
        interval = setInterval(() => {
          remaining -= 1;
          render();
          if (remaining <= 0) {
            clearInterval(interval);
            interval = null;
            running = false;
            remaining = 0;
            startButton.textContent = "Finished";
            display.classList.add("timer-finished");
            if ("Notification" in window && Notification.permission === "granted") {
              new Notification("Locked In", { body: "Your focus session has finished." });
            }
          }
        }, 1000);
      }
    });
    resetButton.addEventListener("click", () => {
      if (interval) clearInterval(interval);
      interval = null;
      running = false;
      remaining = initialMinutes * 60;
      startButton.textContent = "Start";
      display.classList.remove("timer-finished");
      render();
    });
    render();
  }
});
