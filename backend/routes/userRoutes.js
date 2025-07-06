const express=require("express");
const router=express.Router();
const { signupUser, loginUser, updateUser, findUser } = require("../controllers/userController");
const {authMiddleware} =require("../middleswares/auth");

router.post('/signup',signupUser)

router.post("/signin",loginUser);

router.put('/update',authMiddleware,updateUser);


module.exports=router;