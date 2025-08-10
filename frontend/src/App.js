// src/App.js
import React, { useState, useEffect } from 'react';
import './App.css';

// --- STYLES OBJECT ---
const styles = {
  app: {
    backgroundColor: '#111827',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '16px 0',
    fontFamily: 'sans-serif',
    color: 'white',
  },
  container: {
    width: '100%',
    maxWidth: '900px',
    padding: '0 16px',
  },
  header: { textAlign: 'center', marginBottom: '32px' },
  title: {
    fontSize: '3rem', fontWeight: 'bold',
    background: 'linear-gradient(to right, #a855f7, #ec4899, #ef4444)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  subtitle: { color: '#9ca3af', marginTop: '8px', fontSize: '1.1rem' },
  main: {
    backgroundColor: '#1f2937', border: '1px solid #374151',
    borderRadius: '16px', padding: '24px', boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
  },
  inputContainer: { display: 'flex', gap: '16px', flexWrap: 'wrap' },
  input: {
    flexGrow: 1, backgroundColor: '#111827', border: '1px solid #4b5563',
    borderRadius: '8px', padding: '16px', color: 'white', fontSize: '1rem', minWidth: '200px'
  },
  button: {
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
    backgroundColor: '#9333ea', color: 'white', fontWeight: 'bold',
    padding: '0 24px', borderRadius: '8px', fontSize: '1.1rem',
    border: 'none', cursor: 'pointer', transition: 'background-color 0.3s', flexGrow: 1, minWidth: '150px'
  },
  buttonDisabled: { backgroundColor: '#4b5563', cursor: 'not-allowed' },
  error: { color: '#f87171', marginTop: '16px', textAlign: 'center' },
  resultContainer: {
    marginTop: '32px', backgroundColor: '#1f2937', border: '2px dashed #4b5563',
    borderRadius: '16px', minHeight: '400px', display: 'flex',
    flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '16px',
  },
  placeholderText: { color: '#6b7280', textAlign: 'center' },
  memeImage: {
    maxWidth: '100%', height: 'auto', borderRadius: '8px',
    boxShadow: '0 5px 15px rgba(0,0,0,0.2)',
  },
  downloadButton: {
    marginTop: '16px', backgroundColor: '#16a34a', color: 'white',
    fontWeight: 'bold', padding: '10px 24px', borderRadius: '8px',
    textDecoration: 'none', transition: 'background-color 0.3s',
  },
  gallerySection: {
    width: '100%',
    marginTop: '48px',
  },

  sectionTitle: {
  textAlign: 'center',
  fontSize: '2.5rem',
  fontWeight: 'bold',
  background: 'linear-gradient(to right, #a855f7, #ec4899, #ef4444)',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  marginBottom: '8px',
},

  sectionSubtitle: {
  textAlign: 'center',
  fontSize: '1.1rem',
  fontWeight: '500',
  background: 'linear-gradient(to right, #9ca3af, #6b7280)', // gray gradient
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  marginBottom: '24px',
},


  galleryViewport: {
    width: '98%',
    overflow: 'hidden',
    position: 'relative',
    '--mask': 'linear-gradient(to right, transparent, white 10%, white 90%, transparent)',
    mask: 'var(--mask)',
    WebkitMask: 'var(--mask)',
  },
  galleryScrollContainer: {
    display: 'flex',
    gap: '16px',
    padding: '16px 0',
  },
  galleryImageWrapper: {
    flex: '0 0 auto',
    width: '300px',
    height: '300px',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 4px 15px rgba(0,0,0,0.4)',
    backgroundColor: '#000',
  },
  galleryImage: {
    width: '300px',
    height: '300px',
    objectFit: 'contain',
  },
  // --- UPDATED STYLES FOR OG MEME GRID ---
ogGridContainer: {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '20px',
  justifyContent: 'center',
},

ogCard: {
  backgroundColor: '#1f2937',
  borderRadius: '12px',
  overflow: 'hidden',
  boxShadow: '0 6px 18px rgba(0,0,0,0.3)',
  width: '280px',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.3s ease, box-shadow 0.3s ease',
  position: 'relative',
  cursor: 'pointer',
},



ogCardActions: {
  display: 'flex',
  justifyContent: 'space-around',
  padding: '12px',
  backgroundColor: 'rgba(17, 24, 39, 0.9)',
  backdropFilter: 'blur(4px)',
  gap: '10px',
  opacity: 0,
  maxHeight: 0,
  overflow: 'hidden',
  transition: 'opacity 0.3s ease, max-height 0.3s ease',
},

ogButton: {
  backgroundColor: '#9333ea',
  border: 'none',
  color: 'white',
  padding: ' 8px',
  borderRadius: '12px',
  cursor: 'pointer',
  fontSize: '0.9rem',
  fontWeight: '600',
  transition: 'background-color 0.2s',
},

ogCardHover: {
  transform: 'translateY(-4px)',
  boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
},

ogCardActionsVisible: {
  opacity: 1,
  maxHeight: '80px',
}




};

const BACKEND_URL = 'http://127.0.0.1:5000';

const LatestMemesGallery = ({ refreshTrigger }) => {
  const [memes, setMemes] = useState([]);
  const animationDuration = memes.length * 1.5;
  const scrollAnimation = `@keyframes scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }`;

  useEffect(() => {
    const fetchMemes = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/get_latest_memes`);
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) setMemes(data);
      } catch (error) { console.error("Failed to fetch latest memes:", error); }
    };
    fetchMemes();
  }, [refreshTrigger]);

  if (memes.length === 0) return null;

  return (
    <section style={styles.gallerySection}>
      <style>{scrollAnimation}</style>
      <h2 style={styles.sectionTitle}>Latest Creations</h2>
      <p style={styles.sectionSubtitle}>Freshly generated by AI with a punch of humor!</p>
      <div style={styles.galleryViewport}>
        <div style={{ ...styles.galleryScrollContainer, animation: `scroll ${animationDuration}s linear infinite` }}>
          {[...memes, ...memes].map((memeUrl, index) => (
            <div key={index} style={styles.galleryImageWrapper}>
              <img src={`${BACKEND_URL}${memeUrl}`} alt={`Latest meme ${index + 1}`} style={styles.galleryImage} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

const OgMemesGrid = () => {
  const [ogMemes, setOgMemes] = useState([]);
  const [notification, setNotification] = useState('');

  useEffect(() => {
    const fetchOgMemes = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/get_og_memes`);
        const data = await response.json();
        if (Array.isArray(data)) setOgMemes(data);
      } catch (error) { console.error("Failed to fetch OG memes:", error); }
    };
    fetchOgMemes();
  }, []);

  const handleShare = async (memeUrl) => {
    const fullUrl = `${BACKEND_URL}${memeUrl}`;
    const memeTitle = 'Check out this meme from MemeMind!';
    
    if (navigator.share) {
      try {
        const response = await fetch(fullUrl);
        const blob = await response.blob();
        const file = new File([blob], 'meme.jpg', { type: 'image/jpeg' });
        await navigator.share({
          title: memeTitle,
          text: 'Hilarious meme generated by AI!',
          files: [file],
        });
      } catch (error) {
        console.log('Sharing cancelled or failed', error);
      }
    } else {
      try {
        await navigator.clipboard.writeText(fullUrl);
        setNotification('Link copied to clipboard!');
        setTimeout(() => setNotification(''), 2000);
      } catch (err) {
        setNotification('Failed to copy link.');
        setTimeout(() => setNotification(''), 2000);
      }
    }
  };

  if (ogMemes.length === 0) return null;

  return (
    <section style={styles.gallerySection}>
      <h2 style={styles.sectionTitle}>OG Memes</h2>
      <p style={styles.sectionSubtitle}>Humorously Humorous!</p>
      {notification && <p style={{textAlign: 'center', marginBottom: '16px', color: '#34d399'}}>{notification}</p>}
      <div className="og-grid-container">
  {ogMemes.map((memeUrl, index) => (
    <div key={index} className="og-card">
      <img src={`${BACKEND_URL}${memeUrl}`} alt={`OG Meme ${index + 1}`} className="og-card-image" />
      <div className="og-card-actions">
        <a href={`${BACKEND_URL}${memeUrl}`} download className="og-button">Download</a>
        <button onClick={() => handleShare(memeUrl)} className="og-button">Share</button>
      </div>
    </div>
  ))}
</div>

    </section>
  );
};


export default function App() {
  const [topic, setTopic] = useState('');
  const [generatedMeme, setGeneratedMeme] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [galleryRefresh, setGalleryRefresh] = useState(0);

  const handleGenerateMeme = async () => {
    if (!topic.trim()) {
      setError('Please enter a topic to generate a meme.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setGeneratedMeme(null);

    try {
      const response = await fetch(`${BACKEND_URL}/generate_meme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'An unknown server error occurred.' }));
        throw new Error(errorData.error || `Server responded with status: ${response.status}`);
      }
      
      const imageBlob = await response.blob();
      const imageUrl = URL.createObjectURL(imageBlob);
      setGeneratedMeme(imageUrl);
      setGalleryRefresh(prev => prev + 1);

    } catch (err) {
      console.error('Error generating meme:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isLoading) handleGenerateMeme();
  };

  return (
    <div style={styles.app}>
       {/* --- UPDATED GLOBAL STYLES FOR ANIMATIONS --- */}
       <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .og-card { animation: fadeIn 0.5s ease-out forwards; }
        .og-card:hover {
          transform: scale(1.05);
          box-shadow: 0 8px 30px rgba(147, 51, 234, 0.4);
        }
        .og-card:hover .og-card-actions {
          opacity: 1;
          transform: translateY(0);
        }
        .og-button:hover { background-color: #a855f7; }
      `}</style>

      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.title}>MemeBazaar</h1>
          <p style={styles.subtitle}>Not Generating a Meme is NOT FUNNY!</p>
        </header>

        <main style={styles.main}>
          <div style={styles.inputContainer}>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter a topic..."
              style={styles.input}
              disabled={isLoading}
            />
            <button
              onClick={handleGenerateMeme}
              disabled={isLoading}
              style={{ ...styles.button, ...(isLoading && styles.buttonDisabled) }}
            >
              {isLoading ? '...' : 'Generate'}
            </button>
          </div>
          {error && <p style={styles.error}>{error}</p>}
        </main>

        <section style={styles.resultContainer}>
          {isLoading ? (
            <p style={styles.placeholderText}>Aaram se Chai Pio Biscuit Khao...</p>
          ) : generatedMeme ? (
            <>
              <img src={generatedMeme} alt="Generated Meme" style={styles.memeImage} />
              <a href={generatedMeme} download={`mememind-${Date.now()}.jpg`} style={styles.downloadButton}>
                Download
              </a>
            </>
          ) : (
            <p style={styles.placeholderText}>Your masterpiece will appear here</p>
          )}
        </section>
      </div>
      
      <LatestMemesGallery refreshTrigger={galleryRefresh} />
      <OgMemesGrid />
    </div>
  );
}
