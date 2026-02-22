"use strict";
/**
 * Skillize Module - M5
 *
 * Template-driven skill generation from URLs
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectTemplate = exports.getTemplate = exports.templates = exports.listGeneratedSkills = exports.skillize = void 0;
var skillize_1 = require("./skillize");
Object.defineProperty(exports, "skillize", { enumerable: true, get: function () { return skillize_1.skillize; } });
Object.defineProperty(exports, "listGeneratedSkills", { enumerable: true, get: function () { return skillize_1.listGeneratedSkills; } });
var templates_1 = require("./templates");
Object.defineProperty(exports, "templates", { enumerable: true, get: function () { return templates_1.templates; } });
Object.defineProperty(exports, "getTemplate", { enumerable: true, get: function () { return templates_1.getTemplate; } });
Object.defineProperty(exports, "detectTemplate", { enumerable: true, get: function () { return templates_1.detectTemplate; } });
