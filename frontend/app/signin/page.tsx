"use client";
import { AuthButton, InputBox, Redirectstmt } from "../components/subComponents/inputBox";
import { useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";

function Signin() {
  const router = useRouter();

  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement>){
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  async function handleSignin() {
    try {
       await axios.post("http://localhost:4000/user/signin", {
        username: formData.username,
        password: formData.password,
      }).then((response)=>{
        sessionStorage.setItem("token", response.data.token);
        alert("Signin successful!");
        router.push("/Dashboard"); 
      })
      
    } catch (error: any) {
      alert(error?.response?.data?.message || "Signin failed");
    }
  }

  return (
    <div className="flex flex-col justify-center items-center h-screen">
      <div className="border-gray-800 bg-white w-90 h-fit justify-center items-center flex flex-col rounded-md py-6 ">
        <div className="text-3xl font-bold text-black">Sign in</div>

        <InputBox
          type="text"
          placeHolder="Johndoe@gmail.com"
          heading="Username:"
          name="username"
          onChange={handleChange}
        />

        <InputBox
          type="password"
          heading="Password:"
          name="password"
          onChange={handleChange}
        />

        <AuthButton text="Sign In" onClick={handleSignin} />

        <Redirectstmt
          redirectline="Don't Have an Account  ? "
          redirectTo="SignUp"
          href="/signup"
        />
      </div>
    </div>
  );
}

export default Signin;
