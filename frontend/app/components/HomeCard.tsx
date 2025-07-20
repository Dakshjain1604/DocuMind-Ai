import { MouseEventHandler } from "react"
import { Button } from "./Button"

interface HomecardProps{
    heading:string,
    mainText:string,
    ButtonText:string,
    onClick?:MouseEventHandler,
   
}


export function Homecard(props:HomecardProps){
    let bvariant="primary"
    return <div className="border-white h-100 w-80 border-2 rounded-md flex flex-col justify-evenly items-center p-5">
    <h1 className="text-4xl font-semibold">{props.heading}</h1>
    <div className="text justify-center text-center">
    {props.mainText}
    </div>
    <Button variant="primary" size="lg" onClick={props.onClick}>
    {props.ButtonText}
    </Button>
</div>
}