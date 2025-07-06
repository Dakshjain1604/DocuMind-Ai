const  {user} =require ("../db")
const jwt = require("jsonwebtoken");
const bcrypt = require("bcrypt");
const { JWT_SECRET } = require("../config");
const zod = require("zod");
const multer = require('multer');


// Initialize upload middleware


// Create the 'uploads' directory if it doesn't exist
// This is a basic example; in a production environment, consider robust directory creation.



exports.fileUpload = (req, res) => {
    console.log(req.file)
    if (!req.file) {
        return res.status(400).send('No file uploaded.');
    }
    res.json({'File uploaded successfully: ' : req.file.filename});
};
    