'use client'

export function FeedbackButton() {
  const handleFeedback = () => {
    const email = 'hbattle20@gmail.com'
    const subject = encodeURIComponent('Buffett Sheets Feedback')
    const body = encodeURIComponent(`Hi,

I wanted to share some feedback about Buffett Sheets:

[Your feedback here]

---
Browser: ${navigator.userAgent}
Time: ${new Date().toLocaleString()}`)
    
    window.location.href = `mailto:${email}?subject=${subject}&body=${body}`
  }

  return (
    <button
      onClick={handleFeedback}
      className="fixed bottom-4 right-4 bg-blue-500 text-white rounded-full px-4 py-2 shadow-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
      aria-label="Send feedback"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      </svg>
      <span className="hidden sm:inline">Feedback</span>
    </button>
  )
}