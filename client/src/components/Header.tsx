import { FC } from "react";
import { Link } from "wouter";

const Header: FC = () => {
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex justify-between items-center">
          <Link href="/">
            <div className="flex items-center cursor-pointer">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-8 w-8 text-blue-500 mr-3"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M8 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2" />
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
                <path d="m10 12 4 4v-8Z" />
              </svg>
              <h1 className="text-xl font-semibold text-gray-800">Media Specs Extractor</h1>
            </div>
          </Link>
          <a
            href="https://github.com/ffmpeg/ffmpeg"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Documentation <span className="text-xs">↗</span>
          </a>
        </div>
      </div>
    </header>
  );
};

export default Header;
