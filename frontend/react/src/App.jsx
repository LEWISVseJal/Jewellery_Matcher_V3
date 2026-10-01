import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";

import SearchPage from "./pages/SearchPage";
import CataloguePage from "./pages/CataloguePage";
import AddJewelleryPage from "./pages/AddJewelleryPage";


function App() {
  return (
    <BrowserRouter>

      <Routes>

        <Route
          path="/"
          element={<SearchPage />}
        />

        <Route
          path="/catalogue"
          element={<CataloguePage />}
        />

        <Route
          path="/add-jewellery"
          element={<AddJewelleryPage />}
        />

        <Route
          path="*"
          element={<SearchPage />}
        />

      </Routes>

    </BrowserRouter>
  );
}


export default App;