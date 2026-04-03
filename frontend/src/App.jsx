import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import ChordFinder from "./pages/ChordFinder";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/chord-finder" element={<ChordFinder />} />
    </Routes>
  );
}

export default App;