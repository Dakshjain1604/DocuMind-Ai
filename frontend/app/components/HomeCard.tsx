import { MouseEventHandler } from "react"
import { Button } from "./Button"

interface HomecardProps {
    heading: string,
    mainText: string,
    ButtonText: string,
    onClick?: MouseEventHandler,
    disabled?: boolean
}

export function Homecard(props: HomecardProps) {
    return (
        <div className={`
            h-full w-80 rounded-xl flex flex-col justify-between items-center p-6
            bg-white/10 backdrop-blur-sm border border-white/30
            transition-all duration-300
            hover:border-blue-400 hover:shadow-lg hover:shadow-blue-500/20
            ${props.disabled ? 'opacity-60 hover:border-white/30' : ''}
        `}>
            <div className="flex flex-col items-center text-center">
                <h1 className="text-2xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    {props.heading}
                </h1>
                <p className="text-gray-300 mb-4">
                    {props.mainText}
                </p>
            </div>
            
            <Button 
                variant="primary"
                size="lg"
                onClick={props.onClick}
                disabled={props.disabled}
                className={`
                    w-full mt-2
                    ${props.disabled ? 
                        'bg-gray-500 hover:bg-gray-500 cursor-not-allowed' : 
                        'bg-gradient-to-r from-blue-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600'
                    }
                `}
            >
                {props.ButtonText}
            </Button>
        </div>
    )
}