/**
 * Format file size in bytes to a human-readable format with safety checks
 */
export function formatFileSize(bytes: number): string {
  try {
    // Handle non-numeric or invalid inputs
    if (typeof bytes !== 'number' || isNaN(bytes) || !isFinite(bytes)) {
      return 'Unknown size';
    }
    
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(Math.max(1, bytes)) / Math.log(k));
    
    // Ensure we don't exceed the array bounds
    const sizeIndex = Math.min(i, sizes.length - 1);
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[sizeIndex];
  } catch (error) {
    console.error('Error formatting file size:', error);
    return 'Unknown size';
  }
}

/**
 * Format a duration in seconds to HH:MM:SS format
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  const pad = (num: number) => num.toString().padStart(2, '0');
  
  return `${pad(hours)}:${pad(minutes)}:${pad(secs)}`;
}

/**
 * Format a date to a "time ago" string with safety checks for invalid dates
 */
export function formatTimeAgo(date: string | number | Date): string {
  if (!date) return 'recently';
  
  try {
    const now = new Date();
    const past = new Date(date);
    
    // Check if the date is valid
    if (isNaN(past.getTime())) {
      return 'recently';
    }
    
    const diffInSeconds = Math.floor((now.getTime() - past.getTime()) / 1000);
    
    // If the date is in the future (due to clock mismatch), return "just now"
    if (diffInSeconds < 0) {
      return 'just now';
    }
    
    if (diffInSeconds < 60) {
      return 'just now';
    }
    
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) {
      return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`;
    }
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    }
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 30) {
      return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    }
    
    const diffInMonths = Math.floor(diffInDays / 30);
    if (diffInMonths < 12) {
      return `${diffInMonths} month${diffInMonths > 1 ? 's' : ''} ago`;
    }
    
    const diffInYears = Math.floor(diffInMonths / 12);
    return `${diffInYears} year${diffInYears > 1 ? 's' : ''} ago`;
  } catch (error) {
    console.error('Error formatting time:', error);
    return 'recently';
  }
}
