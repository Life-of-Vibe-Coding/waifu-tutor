import { Routes, Route } from "react-router-dom";
import { AppShell } from "./components/AppShell";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />} />
      <Route path="/course-frame" element={<AppShell />} />
    </Routes>
  );
}
