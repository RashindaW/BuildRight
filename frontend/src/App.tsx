import { Routes, Route } from "react-router-dom";
import { Navbar } from "./components/layout/Navbar";
import { CartDrawer } from "./components/cart/CartDrawer";
import { ChatWidget } from "./components/chat/ChatWidget";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import Home from "./pages/Home";
import About from "./pages/About";
import HowToTest from "./pages/HowToTest";
import ItemDetail from "./pages/ItemDetail";
import Checkout from "./pages/Checkout";
import OrderConfirmation from "./pages/OrderConfirmation";
import Orders from "./pages/Orders";
import Login from "./pages/Login";
import Register from "./pages/Register";
import NotFound from "./pages/NotFound";
import AdminDashboard from "./pages/admin/AdminDashboard";
import ManagerDashboard from "./pages/manager/ManagerDashboard";

export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/how-to-test" element={<HowToTest />} />
          <Route path="/item/:slug" element={<ItemDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          {/* checkout + order confirmation work for guests (session-based) */}
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/order/:id" element={<OrderConfirmation />} />
          {/* order history is a logged-in feature */}
          <Route path="/orders" element={<ProtectedRoute><Orders /></ProtectedRoute>} />
          <Route path="/manager" element={<ProtectedRoute roles={["manager", "admin"]}><ManagerDashboard /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute roles={["admin"]}><AdminDashboard /></ProtectedRoute>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <CartDrawer />
      <ChatWidget />
    </div>
  );
}
