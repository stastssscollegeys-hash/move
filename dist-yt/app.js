"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var express_1 = require("express");
var path_1 = require("path");
var routes_1 = require("./youtube-research/routes");
var app = (0, express_1.default)();
app.use(express_1.default.json());
app.use(express_1.default.static(path_1.default.join(__dirname, '..', 'public')));
app.get('/health', function (req, res) {
    res.status(200).json({ status: 'OK' });
});
app.use('/youtube-research', routes_1.youtubeResearchRouter);
exports.default = app;
