import React from 'react';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          PdM Platform
        </h1>
        <p className="text-gray-600 mb-6">
          Production-grade Predictive Maintenance Platform
        </p>
        <div className="space-y-2">
          <a 
            href="http://localhost:8000/docs" 
            className="block w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 text-center"
            target="_blank"
            rel="noopener noreferrer"
          >
            View API Documentation
          </a>
          <a 
            href="http://localhost:8001/docs" 
            className="block w-full bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 text-center"
            target="_blank"
            rel="noopener noreferrer"
          >
            View ML Service
          </a>
        </div>
      </div>
    </div>
  );
}
