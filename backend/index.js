const express=require("express");
const app=express();
app.use(express.json());
const cors = require('cors');
app.use(cors());


//importing the routes
const userRoutes=require("./routes/userRoutes");
const fileRoutes=require('./routes/FileRoutes');

//calling the apis here
app.get("/",(req,res)=>{
    res.send("hi from 3000");
});


app.use('/user',userRoutes);
app.use('/file',fileRoutes);



app.listen(4000);
