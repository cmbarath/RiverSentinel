"use client";

import React, { useState, useRef, useEffect } from "react";

// Language-specific greeting messages
const greetings: Record<string, string> = {
    "English": "Namaste! I am your RiverSentinel AI Assistant. How can I help you today with Ganga's water quality or safety?",
    "हिन्दी": "नमस्ते! मैं आपका RiverSentinel AI सहायक हूं। मैं आज गंगा की जल गुणवत्ता या सुरक्षा के बारे में आपकी कैसे मदद कर सकता हूं?",
    "भोजपुरी": "प्रणाम! हम रउरा RiverSentinel AI सहायक बानी। आज गंगा के पानी के गुणवत्ता भा सुरक्षा के बारे में हम रउरा के कइसे मदद कर सकीलें?",
    "বাংলা": "নমস্কার! আমি আপনার RiverSentinel AI সহায়ক। আজ গঙ্গার জলের গুণমান বা সুরক্ষা সম্পর্কে আমি কীভাবে আপনাকে সাহায্য করতে পারি?"
};

// Language codes for speech recognition
const languageCodes: Record<string, string> = {
    "English": "en-US",
    "हिन्दी": "hi-IN",
    "भोजपुरी": "hi-IN",  // Use Hindi for Bhojpuri
    "বাংলা": "bn-IN"
};

interface SpeechRecognitionResultItem {
    transcript: string;
}

interface SpeechRecognitionResultList {
    [index: number]: SpeechRecognitionResultItem[];
}

interface SpeechRecognitionEventLike {
    results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorLike {
    error: string;
}

interface WebkitSpeechRecognitionLike {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    onresult: ((event: SpeechRecognitionEventLike) => void) | null;
    onerror: ((event: SpeechRecognitionErrorLike) => void) | null;
    onend: (() => void) | null;
    start: () => void;
    stop: () => void;
}

const AIChatbot = () => {
    const [language, setLanguage] = useState("English");
    const [isListening, setIsListening] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [speakingMessageIndex, setSpeakingMessageIndex] = useState<number | null>(null);

    const [messages, setMessages] = useState([
        { role: "bot", text: greetings["English"] }
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [chatbotAvailable, setChatbotAvailable] = useState<boolean | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const recognitionRef = useRef<WebkitSpeechRecognitionLike | null>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    // Check chatbot availability on mount
    useEffect(() => {
        const checkAvailability = async () => {
            try {
                const resp = await fetch(
                    `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'}/api/health`
                );
                const data = await resp.json();
                setChatbotAvailable(!!data.chatbot);
                if (!data.chatbot) {
                    setMessages([{
                        role: "bot",
                        text: "AI chatbot is currently unavailable because the configured AI service is unavailable. The rest of RiverSentinel (sensors, predictions, dashboard) continues to work normally."
                    }]);
                }
            } catch {
                setChatbotAvailable(false);
            }
        };
        checkAvailability();
    }, []);

    // Update greeting when language changes
    useEffect(() => {
        const timer = setTimeout(() => {
            setMessages(prev => {
                if (prev.length <= 1) {
                    return [{ role: "bot", text: greetings[language] || greetings["English"] }];
                }
                return prev;
            });
        }, 0);
        return () => clearTimeout(timer);
    }, [language]);

    // Initialize speech recognition
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const win = window as unknown as {
                SpeechRecognition?: new () => WebkitSpeechRecognitionLike;
                webkitSpeechRecognition?: new () => WebkitSpeechRecognitionLike;
            };
            const SpeechRecognitionClass = win.SpeechRecognition || win.webkitSpeechRecognition;
            if (SpeechRecognitionClass) {
                const recognition = new SpeechRecognitionClass();
                recognition.continuous = false;
                recognition.interimResults = false;

                recognition.onresult = (event: SpeechRecognitionEventLike) => {
                    const transcript = event.results[0][0].transcript;
                    setInput(transcript);
                    setIsListening(false);
                };

                recognition.onerror = (event: SpeechRecognitionErrorLike) => {
                    console.error('Speech recognition error:', event.error);
                    setIsListening(false);
                };

                recognition.onend = () => {
                    setIsListening(false);
                };

                recognitionRef.current = recognition;
            }
        }
    }, []);

    // Update recognition language when language changes
    useEffect(() => {
        if (recognitionRef.current) {
            recognitionRef.current.lang = languageCodes[language] || "en-US";
        }
    }, [language]);

    const handleSend = () => {
        if (!input.trim()) return;

        const userMsg = { role: "user", text: input };
        setMessages(prev => [...prev, userMsg]);
        const currentInput = input;
        setInput("");
        setLoading(true);

        // Call real AI backend with language parameter
        fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'}/api/ai/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: currentInput, language: language })
        })
            .then(res => res.json())
            .then(data => {
                setMessages(prev => [...prev, { role: "bot", text: data.response }]);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setMessages(prev => [...prev, { role: "bot", text: "I'm having trouble connecting to my brain. Please try again later." }]);
                setLoading(false);
            });
    };

    const toggleListening = () => {
        if (!recognitionRef.current) {
            alert('Speech recognition is not supported in your browser. Please use Chrome or Edge.');
            return;
        }

        if (isListening) {
            recognitionRef.current.stop();
            setIsListening(false);
        } else {
            recognitionRef.current.start();
            setIsListening(true);
        }
    };

    const speakText = (text: string, index: number) => {
        if (typeof window === 'undefined') return;

        const synthesis = window.speechSynthesis;

        // Stop any ongoing speech
        if (isSpeaking) {
            synthesis.cancel();
            setIsSpeaking(false);
            setSpeakingMessageIndex(null);
            return;
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = languageCodes[language];
        utterance.rate = 0.9;
        utterance.pitch = 1;

        utterance.onstart = () => {
            setIsSpeaking(true);
            setSpeakingMessageIndex(index);
        };

        utterance.onend = () => {
            setIsSpeaking(false);
            setSpeakingMessageIndex(null);
        };

        utterance.onerror = () => {
            setIsSpeaking(false);
            setSpeakingMessageIndex(null);
        };

        synthesis.speak(utterance);
    };

    return (
        <div className="card" style={{ height: '70vh', padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontSize: '2rem' }}>🤖</span>
                    <div>
                        <h3 style={{ margin: 0 }}>Ganga Sentinel AI</h3>
                        <div style={{ fontSize: '0.8rem', color: chatbotAvailable === false ? '#ef4444' : chatbotAvailable === true ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: chatbotAvailable === false ? '#ef4444' : chatbotAvailable === true ? '#10b981' : '#94a3b8' }}></div>
                            {chatbotAvailable === null ? 'Checking...' : chatbotAvailable ? 'Online' : 'Unavailable'}
                        </div>
                    </div>
                </div>
                <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    style={{ padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border)', fontSize: '0.8rem' }}
                >
                    <option value="English">English</option>
                    <option value="हिन्दी">हिन्दी</option>
                    <option value="भोजपुरी">भोजपुरी</option>
                    <option value="বাংলা">বাংলা</option>
                </select>
            </div>

            <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {messages.map((m, i) => (
                    <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%', display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                        <div style={{ padding: '1rem', borderRadius: '1rem', background: m.role === 'user' ? 'var(--primary)' : '#f1f5f9', color: m.role === 'user' ? 'white' : 'inherit', borderBottomRightRadius: m.role === 'user' ? '0' : '1rem', borderBottomLeftRadius: m.role === 'user' ? '1rem' : '0', flex: 1 }}>
                            {m.text}
                        </div>
                        {m.role === 'bot' && (
                            <button
                                onClick={() => speakText(m.text, i)}
                                style={{
                                    background: speakingMessageIndex === i ? 'var(--primary)' : '#e2e8f0',
                                    border: 'none',
                                    borderRadius: '50%',
                                    width: '36px',
                                    height: '36px',
                                    cursor: 'pointer',
                                    fontSize: '1.2rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    transition: 'all 0.2s',
                                    animation: speakingMessageIndex === i ? 'pulse 1s infinite' : 'none'
                                }}
                                title="Listen to response"
                            >
                                {speakingMessageIndex === i ? '⏸️' : '🔊'}
                            </button>
                        )}
                    </div>
                ))}
                {loading && (
                    <div style={{ alignSelf: 'flex-start', padding: '1rem', borderRadius: '1rem', background: '#f1f5f9' }}>
                        <div style={{ display: 'flex', gap: '4px' }}>
                            <div className="dot" style={{ width: '6px', height: '6px', background: '#94a3b8', borderRadius: '50%', animation: 'bounce 1s infinite' }}></div>
                            <div className="dot" style={{ width: '6px', height: '6px', background: '#94a3b8', borderRadius: '50%', animation: 'bounce 1s infinite 0.2s' }}></div>
                            <div className="dot" style={{ width: '6px', height: '6px', background: '#94a3b8', borderRadius: '50%', animation: 'bounce 1s infinite 0.4s' }}></div>
                        </div>
                        <style>{`@keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }`}</style>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button
                    onClick={toggleListening}
                    style={{
                        background: isListening ? '#ef4444' : '#e2e8f0',
                        border: 'none',
                        borderRadius: '50%',
                        width: '45px',
                        height: '45px',
                        cursor: 'pointer',
                        fontSize: '1.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.2s',
                        animation: isListening ? 'pulse 1s infinite' : 'none'
                    }}
                    title={isListening ? "Stop listening" : "Click to speak"}
                >
                    🎤
                </button>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    placeholder={
                        chatbotAvailable === false
                            ? "AI chatbot unavailable – check GROQ_API_KEY in .env"
                            : isListening
                            ? "Listening..."
                            : "Ask about water quality, flood risk, or safety..."
                    }
                    disabled={chatbotAvailable === false}
                    style={{ flex: 1, padding: '0.75rem 1.5rem', borderRadius: '999px', border: '1px solid var(--border)', outline: 'none', opacity: chatbotAvailable === false ? 0.6 : 1 }}
                />
                <button onClick={handleSend} className="btn btn-primary" disabled={chatbotAvailable === false} style={{ padding: '0.75rem', borderRadius: '50%', width: '45px', height: '45px', opacity: chatbotAvailable === false ? 0.6 : 1 }}>➤</button>
            </div>
            <style>{`
                @keyframes pulse {
                    0%, 100% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.1); opacity: 0.8; }
                }
            `}</style>
        </div>
    );
};

export default AIChatbot;
