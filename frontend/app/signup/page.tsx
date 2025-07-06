"use client";
import {
  AuthButton,
  InputBox,
  Redirectstmt,
} from "../components/subComponents/inputBox";
import { useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

function Signup() {
  const router = useRouter();
  const [success, setSucess] = useState(false);
  const [formData, setFormData] = useState({
    username: "",
    firstname: "",
    lastname: "",
    password: "",
  });
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  }
  async function handleSignup() {
    try {
      await axios
        .post("http://localhost:4000/user/signup", {
          username: formData.username,
          password: formData.password,
          firstname: formData.firstname,
          lastname: formData.lastname,
        })
        .then((response) => {
          alert(response.status);
          console.log(response.data);
          router.push("/signin");
        });
    } catch (error) {
      alert(error);
    }
  }
  return (
    <div className="flex flex-col justify-center items-center h-screen">
      <div className="border-gray-800 bg-white w-90 h-fit justify-center items-center flex flex-col rounded-md py-6 gap-2">
        <div className=" text-3xl font-bold text-black">Sign Up</div>
        <InputBox
          type="text"
          placeHolder="Johndoe@gmail.com"
          heading="Username:"
          name="username"
          onChange={
            handleChange
        }
        />
        <InputBox
          type="text"
          placeHolder="John"
          heading="First Name:"
          name="firstname"
          onChange={
            handleChange
        }
        />
        <InputBox
          type="text"
          placeHolder="Doe"
          heading="Last Name:"
          name="lastname"
          onChange={
            handleChange
        }
        />
        <InputBox
          type="password"
          heading="Password:"
          name="password"
          onChange={
            handleChange
        }
        />
        <AuthButton text="Signup" onClick={handleSignup} />
        <Redirectstmt
          redirectline="Already a User ? "
          redirectTo="Signin"
          href="/signin"
        />
      </div>
    </div>
  );
}

export default Signup;
