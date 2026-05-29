import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md px-4 py-20 text-center">
      <h1 className="text-4xl font-bold text-brand-600">404</h1>
      <p className="mt-2 text-gray-600">That page isn't on the menu.</p>
      <Link to="/" className="btn-primary mt-6">Back to menu</Link>
    </div>
  );
}
