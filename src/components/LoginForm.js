"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LoginForm = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
function LoginForm({ onSubmit }) {
    const [email, setEmail] = (0, react_1.useState)('');
    const [password, setPassword] = (0, react_1.useState)('');
    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit(email, password);
    };
    return ((0, jsx_runtime_1.jsxs)("form", { onSubmit: handleSubmit, className: "login-form", children: [(0, jsx_runtime_1.jsx)("input", { type: "email", value: email, onChange: (e) => setEmail(e.target.value), placeholder: "Email", required: true }), (0, jsx_runtime_1.jsx)("input", { type: "password", value: password, onChange: (e) => setPassword(e.target.value), placeholder: "Password", required: true }), (0, jsx_runtime_1.jsx)("button", { type: "submit", children: "\u30ED\u30B0\u30A4\u30F3" })] }));
}
exports.LoginForm = LoginForm;
