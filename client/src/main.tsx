import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Provide window.global to prevent errors with buffer in browser
window.global = window;

createRoot(document.getElementById("root")!).render(<App />);
