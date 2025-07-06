const express=require("express");
const router=express.Router();
const {authMiddleware} =require("../middleswares/auth");
const multer =require("multer")
const {fileUpload}=require('../controllers/fileController')
const path = require('path');

const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        cb(null, 'uploads/');
    },
    filename: function (req, file, cb) {
        cb(null, file.fieldname + '-' + Date.now() + path.extname(file.originalname));
    }
});
const upload = multer({ storage });


const fs = require('fs');
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
};


router.post('/singleUpload',upload.any(),fileUpload);

module.exports=router;