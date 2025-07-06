// components/ui/Button.tsx
import React from 'react';

type ButtonProps = {
  variant?: 'primary' | 'outline' ;
  size?: 'default' | 'lg';
  className?: string;
  children: React.ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({
  variant = 'primary',
  size = 'default',
  className = '',
  children,
  ...props
}: ButtonProps) {
  // Base button styles
  const baseStyles = 'rounded-md font-medium transition-colors focus:outline-none';
  
  // Variant styles
  const variantStyles = {
    primary: 'bg-white text-black hover:bg-gray-200 hover:scale-110',
    outline: 'border border-white bg-transparent text-white hover:bg-white hover:text-black hover:scale-110',
  };
  
  // Size styles
  const sizeStyles = {
    default: 'px-4 py-2 text-base',
    lg: 'px-8 py-3 text-lg',
  };
  
  // Combine all styles
  const combinedClasses = `
    ${baseStyles}
    ${variantStyles[variant]}
    ${sizeStyles[size]}
    ${className}
  `;

  return (
    <button className={combinedClasses} {...props}>
      {children}
    </button>
  );
}