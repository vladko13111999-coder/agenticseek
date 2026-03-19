import React, { useState, useEffect, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import axios from "axios";
import "./App.css";
import { ThemeToggle } from "./components/ThemeToggle";
import { ResizableLayout } from "./components/ResizableLayout";

const BACKEND_URL = process.env.REACT_APP_API_URL || "";
console.log("Using backend URL:", BACKEND_URL);

function parseMarketingContent(text) {
  if (!text) return [];
  
  const sections = [];
  const patterns = [
    { name: "Facebook Ad", icon: "📘", pattern: /facebook\s*reklama[:\s]*/i },
    { name: "Instagram Post", icon: "📸", pattern: /instagram\s*post[:\s]*/i },
    { name: "Blog Article", icon: "✍️", pattern: /(seo\s*)?blog[:\s]*/i },
    { name: "Competitor Analysis", icon: "📊", pattern: /konkurencia[:\s]*/i },
    { name: "Google Ads", icon: "🔍", pattern: /google\s*ads[:\s]*/i },
    { name: "Email Campaign", icon: "📧", pattern: /email[:\s]*/i },
  ];
  
  const lines = text.split('\n');
  let currentSection = null;
  let currentContent = [];
  
  for (const line of lines) {
    const matched = patterns.find(p => p.pattern.test(line));
    if (matched) {
      if (currentSection) {
        sections.push({ ...currentSection, content: currentContent.join('\n').trim() });
      }
      currentSection = { name: matched.name, icon: matched.icon };
      currentContent = [line.replace(matched.pattern, '').trim()];
    } else if (currentSection) {
      currentContent.push(line);
    } else {
      if (sections.length === 0) {
        currentSection = { name: "Marketing Content", icon: "📋" };
        currentContent.push(line);
      } else {
        currentContent.push(line);
      }
    }
  }
  
  if (currentSection) {
    sections.push({ ...currentSection, content: currentContent.join('\n').trim() });
  }
  
  return sections.length > 0 ? sections : [{ name: "Content", icon: "📋", content: text }];
}

function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentView, setCurrentView] = useState("blocks");
  const [responseData, setResponseData] = useState(null);
  const [isOnline, setIsOnline] = useState(false);
  const [status, setStatus] = useState("Agents ready");
  const [expandedReasoning, setExpandedReasoning] = useState(new Set());
  const messagesEndRef = useRef(null);

  // Marketing generation state
  const [marketingUrl, setMarketingUrl] = useState("");
  const [marketingLang, setMarketingLang] = useState("sk");
  const [marketingTaskId, setMarketingTaskId] = useState(null);
  const [marketingStatus, setMarketingStatus] = useState(null);
  const [marketingResult, setMarketingResult] = useState(null);
  const [isMarketingGenerating, setIsMarketingGenerating] = useState(false);

  // Video generation state
  const [videoUrl, setVideoUrl] = useState("");
  const [videoLang, setVideoLang] = useState("sk");
  const [videoDuration, setVideoDuration] = useState("15");
  const [videoTaskId, setVideoTaskId] = useState(null);
  const [videoStatus, setVideoStatus] = useState(null);
  const [videoResult, setVideoResult] = useState(null);
  const [isVideoGenerating, setIsVideoGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState("marketing");

  const fetchLatestAnswer = useCallback(async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/latest_answer`);
      const data = res.data;

      updateData(data);
      if (!data.answer || data.answer.trim() === "") {
        return;
      }
      const normalizedNewAnswer = normalizeAnswer(data.answer);
      const answerExists = messages.some(
        (msg) => normalizeAnswer(msg.content) === normalizedNewAnswer
      );
      if (!answerExists) {
        setMessages((prev) => [
          ...prev,
          {
            type: "agent",
            content: data.answer,
            reasoning: data.reasoning,
            agentName: data.agent_name,
            status: data.status,
            uid: data.uid,
          },
        ]);
        setStatus(data.status);
        scrollToBottom();
      } else {
        console.log("Duplicate answer detected, skipping:", data.answer);
      }
    } catch (error) {
      console.error("Error fetching latest answer:", error);
    }
  }, [messages]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      checkHealth();
      fetchLatestAnswer();
      fetchScreenshot();
    }, 3000);
    return () => clearInterval(intervalId);
  }, [fetchLatestAnswer]);

  // Poll for marketing task status
  useEffect(() => {
    if (!marketingTaskId) return;
    
    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${BACKEND_URL}/status/${marketingTaskId}`);
        const data = res.data;
        setMarketingStatus(data.status);
        
        if (data.status === "completed") {
          setMarketingResult(data.result);
          setIsMarketingGenerating(false);
          clearInterval(pollInterval);
        } else if (data.status === "failed") {
          setError(data.error || "Marketing generation failed");
          setIsMarketingGenerating(false);
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error("Error polling task status:", err);
      }
    }, 2000);
    
    return () => clearInterval(pollInterval);
  }, [marketingTaskId]);

  // Poll for video task status
  useEffect(() => {
    if (!videoTaskId) return;
    
    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${BACKEND_URL}/status/${videoTaskId}`);
        const data = res.data;
        setVideoStatus(data.status);
        
        if (data.status === "completed") {
          setVideoResult(data.result);
          setIsVideoGenerating(false);
          clearInterval(pollInterval);
        } else if (data.status === "failed") {
          setError(data.error || "Video generation failed");
          setIsVideoGenerating(false);
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error("Error polling video task status:", err);
      }
    }, 2000);
    
    return () => clearInterval(pollInterval);
  }, [videoTaskId]);

  const checkHealth = async () => {
    try {
      await axios.get(`${BACKEND_URL}/health`);
      setIsOnline(true);
      console.log("System is online");
    } catch {
      setIsOnline(false);
      console.log("System is offline");
    }
  };

  const fetchScreenshot = async () => {
    try {
      const timestamp = new Date().getTime();
      const res = await axios.get(
        `${BACKEND_URL}/screenshots/updated_screen.png?timestamp=${timestamp}`,
        {
          responseType: "blob",
        }
      );
      console.log("Screenshot fetched successfully");
      const imageUrl = URL.createObjectURL(res.data);
      setResponseData((prev) => {
        if (prev?.screenshot && prev.screenshot !== "placeholder.png") {
          URL.revokeObjectURL(prev.screenshot);
        }
        return {
          ...prev,
          screenshot: imageUrl,
          screenshotTimestamp: new Date().getTime(),
        };
      });
    } catch (err) {
      console.error("Error fetching screenshot:", err);
      setResponseData((prev) => ({
        ...prev,
        screenshot: "placeholder.png",
        screenshotTimestamp: new Date().getTime(),
      }));
    }
  };

  const normalizeAnswer = (answer) => {
    return answer
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ")
      .replace(/[.,!?]/g, "");
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const toggleReasoning = (messageIndex) => {
    setExpandedReasoning((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(messageIndex)) {
        newSet.delete(messageIndex);
      } else {
        newSet.add(messageIndex);
      }
      return newSet;
    });
  };

  const updateData = (data) => {
    setResponseData((prev) => ({
      ...prev,
      blocks: data.blocks || prev.blocks || null,
      done: data.done,
      answer: data.answer,
      agent_name: data.agent_name,
      status: data.status,
      uid: data.uid,
    }));
  };

  const handleStop = async (e) => {
    e.preventDefault();
    checkHealth();
    setIsLoading(false);
    setError(null);
    try {
      await axios.get(`${BACKEND_URL}/stop`);
      setStatus("Requesting stop...");
    } catch (err) {
      console.error("Error stopping the agent:", err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    checkHealth();
    if (!query.trim()) {
      console.log("Empty query");
      return;
    }
    setMessages((prev) => [...prev, { type: "user", content: query }]);
    setIsLoading(true);
    setError(null);

    try {
      console.log("Sending query:", query);
      setQuery("waiting for response...");
      const res = await axios.post(`${BACKEND_URL}/query`, {
        query,
        tts_enabled: false,
      });
      setQuery("Enter your query...");
      console.log("Response:", res.data);
      const data = res.data;
      updateData(data);
    } catch (err) {
      console.error("Error:", err);
      setError("Failed to process query.");
      setMessages((prev) => [
        ...prev,
        { type: "error", content: "Error: Unable to get a response." },
      ]);
    } finally {
      console.log("Query completed");
      setIsLoading(false);
      setQuery("");
    }
  };

  const handleGetScreenshot = async () => {
    try {
      setCurrentView("screenshot");
    } catch (err) {
      setError("Browser not in use");
    }
  };

  const handleGenerateMarketing = async (e) => {
    e.preventDefault();
    if (!marketingUrl.trim()) {
      setError("URL is required");
      return;
    }
    
    setError(null);
    setMarketingResult(null);
    setMarketingStatus(null);
    setIsMarketingGenerating(true);
    
    try {
      const res = await axios.post(`${BACKEND_URL}/generate`, {
        url: marketingUrl,
        lang: marketingLang
      });
      setMarketingTaskId(res.data.task_id);
      setMarketingStatus(res.data.status);
    } catch (err) {
      console.error("Error starting generation:", err);
      setError("Failed to start generation");
      setIsMarketingGenerating(false);
    }
  };

  const handleGenerateVideo = async (e) => {
    e.preventDefault();
    if (!videoUrl.trim()) {
      setError("URL is required");
      return;
    }
    
    setError(null);
    setVideoResult(null);
    setVideoStatus(null);
    setIsVideoGenerating(true);
    
    try {
      const res = await axios.post(`${BACKEND_URL}/generate_video`, {
        url: videoUrl,
        lang: videoLang,
        duration: parseInt(videoDuration)
      });
      setVideoTaskId(res.data.task_id);
      setVideoStatus(res.data.status);
    } catch (err) {
      console.error("Error starting video generation:", err);
      setError("Failed to start video generation");
      setIsVideoGenerating(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-brand">
          <div className="brand-text">
            <h1>Tvojton.online</h1>
          </div>
        </div>
        <div className="header-status">
          <div
            className={`status-indicator ${isOnline ? "online" : "offline"}`}
          >
            <div className="status-dot"></div>
            <span className="status-text">
              {isOnline ? "Online" : "Offline"}
            </span>
          </div>
        </div>
        <div className="header-actions">
          <div>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <div className="marketing-section">
        <div className="tab-selector">
          <button
            className={activeTab === "marketing" ? "active" : ""}
            onClick={() => setActiveTab("marketing")}
          >
            Marketing
          </button>
          <button
            className={activeTab === "video" ? "active" : ""}
            onClick={() => setActiveTab("video")}
          >
            Video
          </button>
        </div>
        
        {activeTab === "marketing" && (
          <>
            <h2>Marketing Generator</h2>
            <form onSubmit={handleGenerateMarketing} className="marketing-form">
              <input
                type="url"
                value={marketingUrl}
                onChange={(e) => setMarketingUrl(e.target.value)}
                placeholder="Enter product URL..."
                disabled={isMarketingGenerating}
                className="marketing-url-input"
              />
              <select
                value={marketingLang}
                onChange={(e) => setMarketingLang(e.target.value)}
                disabled={isMarketingGenerating}
                className="marketing-lang-select"
              >
                <option value="sk">Slovak</option>
                <option value="cs">Czech</option>
                <option value="hr">Croatian</option>
                <option value="en">English</option>
              </select>
              <button
                type="submit"
                disabled={isMarketingGenerating}
                className="marketing-generate-btn"
              >
                {isMarketingGenerating ? "Generating..." : "Generate"}
              </button>
            </form>
            {isMarketingGenerating && marketingStatus && (
              <div className="marketing-status">
                <div className="loading-spinner"></div>
                <span>Status: {marketingStatus}</span>
              </div>
            )}
            {marketingResult && (
              <div className="marketing-cards">
                <h3 className="marketing-cards-title">Generated Marketing Content</h3>
                {parseMarketingContent(marketingResult.answer).map((section, index) => (
                  <div key={index} className="marketing-card">
                    <div className="marketing-card-header">
                      <span className="marketing-card-icon">{section.icon}</span>
                      <h4>{section.name}</h4>
                    </div>
                    <div className="marketing-card-content">
                      <pre>{section.content}</pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
        
        {activeTab === "video" && (
          <>
            <h2>Video Generator</h2>
            <form onSubmit={handleGenerateVideo} className="marketing-form">
              <input
                type="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Enter product URL..."
                disabled={isVideoGenerating}
                className="marketing-url-input"
              />
              <select
                value={videoDuration}
                onChange={(e) => setVideoDuration(e.target.value)}
                disabled={isVideoGenerating}
                className="marketing-lang-select"
              >
                <option value="5">5 sekúnd</option>
                <option value="10">10 sekúnd</option>
                <option value="15">15 sekúnd</option>
                <option value="30">30 sekúnd</option>
              </select>
              <select
                value={videoLang}
                onChange={(e) => setVideoLang(e.target.value)}
                disabled={isVideoGenerating}
                className="marketing-lang-select"
              >
                <option value="sk">Slovenčina</option>
                <option value="en">Angličtina</option>
                <option value="hr">Chorvátčina</option>
              </select>
              <button
                type="submit"
                disabled={isVideoGenerating}
                className="marketing-generate-btn video-btn"
              >
                {isVideoGenerating ? "Generujem..." : "Generovať video"}
              </button>
            </form>
            {isVideoGenerating && videoStatus && (
              <div className="marketing-status">
                <div className="loading-spinner"></div>
                <span>Status: {videoStatus === "analyzing" && "Analyzujem URL..."}
                      {videoStatus === "generating_script" && "Vytváram scenár..."}
                      {videoStatus === "creating_video" && "Vytváram video..."}
                      {videoStatus === "pending" && "Čakám..."}
                      {videoStatus === "processing" && "Spracovávam..."}</span>
              </div>
            )}
            {videoResult && (
              <div className="video-result">
                <h3>Vygenerované video</h3>
                <p className="product-name">Produkt: {videoResult.product_name}</p>
                <div className="video-script">
                  <h4>Scenár:</h4>
                  <pre>{videoResult.script}</pre>
                </div>
                {videoResult.video_url && (
                  <div className="video-player">
                    <video 
                      controls 
                      width="100%" 
                      src={`${BACKEND_URL}${videoResult.video_url}`}
                    >
                      Váš prehliadač nepodporuje video.
                    </video>
                    <a 
                      href={`${BACKEND_URL}${videoResult.video_url}`}
                      download
                      className="download-btn"
                    >
                      Stiahnuť video
                    </a>
                  </div>
                )}
              </div>
            )}
          </>
        )}
        
        {error && <p className="error">{error}</p>}
      </div>
      <main className="main">
        <ResizableLayout initialLeftWidth={50}>
          <div className="chat-section">
            <h2>Chat Interface</h2>
            <div className="messages">
              {messages.length === 0 ? (
                <p className="placeholder">
                  No messages yet. Type below to start!
                </p>
              ) : (
                messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`message ${
                      msg.type === "user"
                        ? "user-message"
                        : msg.type === "agent"
                        ? "agent-message"
                        : "error-message"
                    }`}
                  >
                    <div className="message-header">
                      {msg.type === "agent" && (
                        <span className="agent-name">{msg.agentName}</span>
                      )}
                      {msg.type === "agent" &&
                        msg.reasoning &&
                        expandedReasoning.has(index) && (
                          <div className="reasoning-content">
                            <ReactMarkdown>{msg.reasoning}</ReactMarkdown>
                          </div>
                        )}
                      {msg.type === "agent" && (
                        <button
                          className="reasoning-toggle"
                          onClick={() => toggleReasoning(index)}
                          title={
                            expandedReasoning.has(index)
                              ? "Hide reasoning"
                              : "Show reasoning"
                          }
                        >
                          {expandedReasoning.has(index) ? "▼" : "▶"} Reasoning
                        </button>
                      )}
                    </div>
                    <div className="message-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
            {isOnline && <div className="loading-animation">{status}</div>}
            {!isLoading && !isOnline && (
              <p className="loading-animation">
                System offline. Deploy backend first.
              </p>
            )}
            <form onSubmit={handleSubmit} className="input-form">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type your query..."
                disabled={isLoading}
              />
              <div className="action-buttons">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="icon-button"
                  aria-label="Send message"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={handleStop}
                  className="icon-button stop-button"
                  aria-label="Stop processing"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect
                      x="6"
                      y="6"
                      width="12"
                      height="12"
                      fill="currentColor"
                      rx="2"
                    />
                  </svg>
                </button>
              </div>
            </form>
          </div>

          <div className="computer-section">
            <h2>Computer View</h2>
            <div className="view-selector">
              <button
                className={currentView === "blocks" ? "active" : ""}
                onClick={() => setCurrentView("blocks")}
              >
                Editor View
              </button>
              <button
                className={currentView === "screenshot" ? "active" : ""}
                onClick={
                  responseData?.screenshot
                    ? () => setCurrentView("screenshot")
                    : handleGetScreenshot
                }
              >
                Browser View
              </button>
            </div>
            <div className="content">
              {error && <p className="error">{error}</p>}
              {currentView === "blocks" ? (
                <div className="blocks">
                  {responseData &&
                  responseData.blocks &&
                  Object.values(responseData.blocks).length > 0 ? (
                    Object.values(responseData.blocks).map((block, index) => (
                      <div key={index} className="block">
                        <p className="block-tool">Tool: {block.tool_type}</p>
                        <pre>{block.block}</pre>
                        <p className="block-feedback">
                          Feedback: {block.feedback}
                        </p>
                        {block.success ? (
                          <p className="block-success">Success</p>
                        ) : (
                          <p className="block-failure">Failure</p>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="block">
                      <p className="block-tool">Tool: No tool in use</p>
                      <pre>No file opened</pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="screenshot">
                  <img
                    src={responseData?.screenshot || "placeholder.png"}
                    alt="Screenshot"
                    onError={(e) => {
                      e.target.src = "placeholder.png";
                      console.error("Failed to load screenshot");
                    }}
                    key={responseData?.screenshotTimestamp || "default"}
                  />
                </div>
              )}
            </div>
          </div>
        </ResizableLayout>
      </main>
    </div>
  );
}

export default App;
