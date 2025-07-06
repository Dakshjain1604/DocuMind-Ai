const mongoose =require("mongoose");

const { MONGODB_URL } = require("./config");

const db=mongoose.connect(MONGODB_URL);

const userSchema=new mongoose.Schema({
    username:{type:String,unique:true},
    password:String,
    firstname:String,
    lastname:String
})



const user=mongoose.model("user",userSchema);

module.exports={
    user
}
