import { useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiUploadCloud,
  FiZap,
  FiSettings,
  FiRefreshCw,
  FiStar,
  FiUser,
  FiUserCheck,
  FiCamera,
  FiEdit3,
  FiX,
} from 'react-icons/fi';
import { PiMagicWand } from 'react-icons/pi';
import clsx from 'clsx';

const DEFAULT_BACKEND = (
  import.meta.env.VITE_API_BASE_URL ?? 'https://hairstyle-backend-service-163900448961.asia-southeast1.run.app'
).replace(/\/$/, '');
const MAX_STREAM_COUNT = 6;
const FACE_SUFFIX = ' keep my face same';

const PROMPTS = {
  female: [
    'Create a modern textured bob with copper highlights',
    'Transform into a sleek pixie cut with side-swept bangs',
    'Long wavy layers with sun-kissed balayage',
    'High-fashion editorial updo with bold volume',
  ],
  male: [
    'Craft a clean skin fade with a textured quiff',
    'Medium-length messy waves with natural highlights',
    'Classic pompadour with a sharp undercut',
    'Laid-back surfer cut with tousled texture',
  ],
};

const RECOMMEND_PROMPT = 'you are an expert hairstylist, change my hairstyle based on my face, pls keep my face same';

function MetricCard({ icon: Icon, value, label }) {
  return (
    <div className="metric-card">
      <div className="metric-card__icon">
        <Icon />
      </div>
      <div>
        <p className="metric-card__value">{value}</p>
        <p className="metric-card__label">{label}</p>
      </div>
    </div>
  );
}

function GenderToggle({ value, onChange }) {
  return (
    <div className="gender-toggle">
      <button
        type="button"
        className={clsx('gender-toggle__button', { 'gender-toggle__button--active': value === 'female' })}
        onClick={() => onChange('female')}
      >
        <FiUserCheck /> Female styles
      </button>
      <button
        type="button"
        className={clsx('gender-toggle__button', { 'gender-toggle__button--active': value === 'male' })}
        onClick={() => onChange('male')}
      >
        <FiUser /> Male styles
      </button>
    </div>
  );
}

function StatusBanner({ message, kind }) {
  if (!message) {
    return null;
  }
  const className = clsx('status-banner', {
    'status-banner--success': kind === 'success',
    'status-banner--error': kind === 'error',
    'status-banner--warning': kind === 'warning',
    'status-banner--info': kind === 'info',
  });
  return <p className={className}>{message}</p>;
}

function ensureFaceSuffix(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return '';
  }
  return trimmed.endsWith(FACE_SUFFIX) ? trimmed : `${trimmed}${FACE_SUFFIX}`;
}

function App() {
  const [gender, setGender] = useState('female');
  const [prompt, setPrompt] = useState(ensureFaceSuffix(PROMPTS.female[0]));
  const [count, setCount] = useState(1);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusKind, setStatusKind] = useState('idle');
  const [results, setResults] = useState([]);
  const [lightboxImage, setLightboxImage] = useState(null);
  const [cameraError, setCameraError] = useState('');
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isCameraLoading, setIsCameraLoading] = useState(false);

  const [isPromptPanelOpen, setIsPromptPanelOpen] = useState(false);

  const videoRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  const buttonLabel = useMemo(
    () => (count > 1 ? 'Generate collection' : 'Generate look'),
    [count]
  );

  const sanitizedBaseUrl = DEFAULT_BACKEND;

  const resetInterface = () => {
    setResults([]);
    setStatusMessage('');
    setStatusKind('idle');
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      setImageFile(null);
      setImagePreview('');
      resetInterface();
      return;
    }

    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    resetInterface();
    stopCamera();
  };

  const handleClearImage = () => {
    setImageFile(null);
    setImagePreview('');
    resetInterface();
  };

  const startCamera = async () => {
    stopCamera();
    setCameraError('');
    setIsCameraLoading(true);
    setIsCameraActive(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        const playPromise = videoRef.current.play();
        if (playPromise && typeof playPromise.then === 'function') {
          playPromise.catch(() => {});
        }
      }
    } catch (error) {
      setCameraError('Camera access was denied. Please allow camera permissions.');
      setIsCameraActive(false);
    } finally {
      setIsCameraLoading(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 720;
    canvas.height = video.videoHeight || 720;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) {
        setCameraError('Could not capture photo. Try again.');
        return;
      }
      const file = new File([blob], 'camera-capture.png', { type: 'image/png' });
      stopCamera();
      setImageFile(file);
      setImagePreview(URL.createObjectURL(blob));
      resetInterface();
    }, 'image/png');
  };

  const handleGenderChange = (nextGender) => {
    setGender(nextGender);
    const defaultPrompt = ensureFaceSuffix(PROMPTS[nextGender][0]);
    setPrompt(defaultPrompt);
  };

  const handleUsePrompt = (value) => {
    setPrompt(ensureFaceSuffix(value));
  };

  const handleRecommendPrompt = () => {
    handleUsePrompt(RECOMMEND_PROMPT);
  };

  const togglePromptPanel = () => {
    setIsPromptPanelOpen((prev) => !prev);
  };

  const handlePromptChange = (event) => {
    setPrompt(ensureFaceSuffix(event.target.value));
  };

  const appendResult = (index, imageSrc) => {
    setResults((prev) => [...prev, { index, imageSrc }]);
  };

  const fetchSingleResult = async (formData) => {
    const response = await fetch(`${sanitizedBaseUrl}/hairstyle`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    appendResult(0, objectUrl);
    setStatusMessage('New hairstyle generated!');
    setStatusKind('success');
  };

  const fetchStreamResults = async (formData) => {
    const response = await fetch(`${sanitizedBaseUrl}/hairstyles/stream`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with status ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Streaming is not supported in this browser.');
    }

    const decoder = new TextDecoder();
    let bufferedText = '';

    const processLine = (line) => {
      if (!line.trim()) {
        return;
      }

      const payload = JSON.parse(line);
      if (payload.error) {
        throw new Error(payload.error);
      }

      const base64Image = payload.image_base64;
      if (!base64Image) {
        return;
      }

      const numericIndex = Number(payload.index);
      const safeIndex = Number.isNaN(numericIndex) ? -1 : numericIndex;
      appendResult(safeIndex, `data:image/png;base64,${base64Image}`);
      setStatusKind('success');
      setStatusMessage('Hairstyles are arriving...');
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      bufferedText += decoder.decode(value, { stream: true });
      const lines = bufferedText.split('\n');
      bufferedText = lines.pop() ?? '';

      for (const line of lines) {
        try {
          processLine(line);
        } catch (error) {
          setStatusKind('error');
          setStatusMessage(error instanceof Error ? error.message : 'Error reading stream data.');
          throw error instanceof Error ? error : new Error('Error reading stream data.');
        }
      }
    }

    if (bufferedText.trim()) {
      try {
        processLine(bufferedText);
      } catch (error) {
        setStatusKind('error');
        setStatusMessage(error instanceof Error ? error.message : 'Error reading stream data.');
        throw error instanceof Error ? error : new Error('Error reading stream data.');
      }
    }

    setStatusMessage('All hairstyles generated!');
    setStatusKind('success');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!imageFile) {
      setStatusKind('warning');
      setStatusMessage('Please choose an image first.');
      return;
    }

    if (!prompt.trim()) {
      setStatusKind('warning');
      setStatusMessage('Please fill the prompt field.');
      return;
    }

    const formData = new FormData();
    formData.append('prompt', ensureFaceSuffix(prompt));
    formData.append('count', String(count));
    formData.append('image', imageFile);

    setIsLoading(true);
    setStatusKind('info');
    setStatusMessage('Contacting the service...');
    setResults([]);

    try {
      if (count === 1) {
        await fetchSingleResult(formData);
      } else {
        await fetchStreamResults(formData);
      }
    } catch (error) {
      console.error(error);
      setStatusKind('error');
      setStatusMessage(error instanceof Error ? error.message : 'Something went wrong.');
    } finally {
      setIsLoading(false);
    }
  };

  const orderedResults = useMemo(
    () => [...results].sort((a, b) => a.index - b.index),
    [results]
  );

  const scrollToWorkspace = () => {
    const el = document.getElementById('workspace');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const promptLibrary = PROMPTS[gender];

  return (
    <div className="page">
      <div className="page__inner">
        <section className="hero">
          <motion.div
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="hero__content"
          >
            <span className="hero__badge">Nano Hairstyle Studio</span>
            <h1>YOUR PERSONAL AI HAIRSTYLIST</h1>
            <p>
              Discover looks you love without leaving home. Upload a photo and see premium
              hairstyle concepts stream in seconds.
            </p>
            <div className="hero__actions">
              <button type="button" className="btn btn--primary" onClick={scrollToWorkspace}>
                Start designing
              </button>
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="hero__metrics"
          >
            <MetricCard icon={FiZap} value="< 30s" label="Average render time" />
            <MetricCard icon={FiStar} value="4K" label="Upscaled image quality" />
            <MetricCard icon={FiSettings} value="100+" label="Style prompt variations" />
          </motion.div>
        </section>

        <section className="workspace" id="workspace">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.5 }}
            className="column column--controls"
          >
            <div className="card card--soft">
              <div className="card__header">
                <h2>1 · Upload portrait</h2>
                <span className="card__hint">
                  Best results start with even lighting and a centered face
                </span>
              </div>
              <label className="dropzone">
                <input type="file" accept="image/png,image/jpeg" onChange={handleFileChange} />
                <FiUploadCloud size={24} />
                <span className="dropzone__text">
                  Drag & drop or <span className="dropzone__action">choose a file</span>
                </span>
              </label>
              <div className="camera">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={isCameraActive ? stopCamera : startCamera}
                  disabled={isCameraLoading}
                >
                  <FiCamera /> {isCameraActive ? 'Close camera' : 'Use camera'}
                </button>
                {isCameraLoading && <span className="camera__hint">Starting camera…</span>}
                {cameraError && <span className="camera__error">{cameraError}</span>}
                {isCameraActive && (
                  <div className="camera__preview">
                    <video ref={videoRef} autoPlay playsInline muted />
                    <div className="camera__actions">
                      <button type="button" className="btn btn--primary" onClick={capturePhoto}>
                        Capture photo
                      </button>
                    </div>
                  </div>
                )}
              </div>
              <AnimatePresence>
                {imagePreview && (
                  <motion.div
                    key="preview"
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 12 }}
                    className="preview"
                  >
                    <img src={imagePreview} alt="Selected portrait" />
                    <button type="button" className="btn btn--ghost" onClick={handleClearImage}>
                      Remove image
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="card">
              <div className="card__header">
                <h2>2 · Craft prompt</h2>
                <span className="card__hint">Select a vibe then tailor the details</span>
              </div>

              <div className="prompt-actions">
                <button type="button" className="btn btn--ghost" onClick={handleRecommendPrompt}>
                  <PiMagicWand />
                  Recommend me
                </button>
                <button
                  type="button"
                  className={clsx('btn btn--ghost', { 'btn--ghost-active': isPromptPanelOpen })}
                  onClick={togglePromptPanel}
                  aria-expanded={isPromptPanelOpen}
                  aria-controls="prompt-panel"
                >
                  <FiEdit3 />
                  Hairstyle prompts
                </button>
              </div>

              <AnimatePresence initial={false}>
                {isPromptPanelOpen && (
                  <motion.div
                    key="prompt-panel"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                    style={{ overflow: 'hidden' }}
                  >
                    <div className="prompt-panel" id="prompt-panel">
                      <GenderToggle value={gender} onChange={handleGenderChange} />
                      <div className="prompt-library">
                        {promptLibrary.map((item) => (
                          <button
                            key={item}
                            type="button"
                            className={clsx('prompt-chip', { 'prompt-chip--active': ensureFaceSuffix(item) === prompt })}
                            onClick={() => handleUsePrompt(item)}
                          >
                            {item}
                          </button>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <form className="form" onSubmit={handleSubmit}>
                <label className="form__field">
                  <span className="form__label">Custom prompt</span>
                  <textarea
                    value={prompt}
                    onChange={handlePromptChange}
                    rows={4}
                    placeholder="Describe the cut, texture, and colour you want"
                  />
                </label>

                <div className="form__split">
                  <label className="form__field">
                    <span className="form__label">Variations</span>
                    <input
                      type="number"
                      min={1}
                      max={MAX_STREAM_COUNT}
                      value={count}
                      onChange={(event) => setCount(Number(event.target.value))}
                    />
                  </label>
                </div>

                <button type="submit" className="btn btn--primary" disabled={isLoading || !imageFile}>
                  {isLoading ? 'Designing...' : buttonLabel}
                </button>
              </form>

              <StatusBanner message={statusMessage} kind={statusKind} />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.5 }}
            className="column column--results"
          >
            <div className="card card--results">
              <div className="card__header card__header--results">
                <div>
                  <h2>3 · Showcase gallery</h2>
                  <span className="card__hint">Generated looks appear below in real time</span>
                </div>
                <button type="button" className="refresh" onClick={resetInterface}>
                  <FiRefreshCw />
                  Clear board
                </button>
              </div>

              <div className="results-area">
                {isLoading && (
                  <div className="loading">
                    <span className="loading__spinner" />
                    <p>Generating hairstyles...</p>
                  </div>
                )}

                {!isLoading && orderedResults.length === 0 && (
                  <div className="empty">
                    <p>No images yet. Upload a portrait and click generate.</p>
                  </div>
                )}

                <AnimatePresence mode="popLayout">
                  {orderedResults.length > 0 && (
                    <motion.div
                      key="results"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="results-grid"
                    >
                      {orderedResults.map((item, position) => (
                        <motion.figure
                          key={`${item.index}-${position}`}
                          layout
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.25, delay: position * 0.07 }}
                          className="result-card"
                          onClick={() => setLightboxImage(item.imageSrc)}
                        >
                          <img src={item.imageSrc} alt={`Generated hairstyle ${position + 1}`} />
                          <figcaption>Style {position + 1}</figcaption>
                        </motion.figure>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        </section>

        <AnimatePresence>
          {lightboxImage && (
            <motion.div
              className="lightbox"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setLightboxImage(null)}
            >
              <motion.div
                className="lightbox__content"
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                onClick={(event) => event.stopPropagation()}
              >
                <button type="button" className="lightbox__close" onClick={() => setLightboxImage(null)}>
                  <FiX />
                </button>
                <img src={lightboxImage} alt="Generated hairstyle full screen" />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;


