import { MouseEventHandler } from "react";
interface inputProps{
    name:string,
    placeHolder?:string,
    type:string,
    heading:string
    onChange:(event: React.ChangeEvent<HTMLInputElement>) => void;
}

export function InputBox(props:inputProps){

return <div className="w-full justify-center flex flex-col px-8 text-white">
    <div className="text-black ">{props.heading}</div>
   <input name={props.name} onChange={props.onChange} type={props.type}  placeholder={props.placeHolder} className="bg-gray-300 text-black border-black px-3 py-2 rounded-md">
   </input>
   </div>
}


interface Redirect{
    redirectline:string,
    redirectTo:string,
    href:string
}

export function Redirectstmt(props:Redirect){
    return <div className=" text-sm justify-center text-black hover:cursor-pointer mt-3">
        {props.redirectline}<a href={props.href} className="font-bold ml-0.2 underline w-fit hover:text-blue-600 hover:scale-110">{props.redirectTo}</a>
    </div>
}

interface ButtonProps{
    text:string,
    onClick?:MouseEventHandler
}

export function AuthButton(props:ButtonProps){
       
        return(
    <div className="w-full justify-center flex flex-col px-8 pt-5 items-center hover:scale-105" onClick={props.onClick}>
            <button className="text-white bg-black rounded-md px-3 py-2 w-[95%]"> {props.text}</button>
       </div>);
        
        
}