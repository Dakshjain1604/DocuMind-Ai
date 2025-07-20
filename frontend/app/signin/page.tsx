'use client'
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';

export default function SigninPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await axios.post('/api/auth/signin', { email, password });
      setSuccess('Signin successful! Redirecting...');
      setTimeout(() => router.push('/Dashboard'), 1500);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Signin failed');
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen ">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-lg shadow-md w-full max-w-md text-black">
        <h2 className="text-2xl font-bold mb-6 text-center">Sign In</h2>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full mb-4 px-4 py-2 border rounded"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full mb-4 px-4 py-2 border rounded"
          required
        />
        <button type="submit" className="w-full bg-black text-white py-2 rounded hover:bg-gray-800 transition">Sign In</button>
        {error && <div className="text-red-600 mt-4 text-center">{error}</div>}
        {success && <div className="text-green-600 mt-4 text-center">{success}</div>}
        <div className="mt-4 text-center">
          Don't have an account? <a href="/signup" className="text-blue-600 underline">Sign Up</a>
        </div>
      </form>
    </div>
  );
} 