import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [image, setImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [serverStatus, setServerStatus] = useState("Checking...");

  const [params, setParams] = useState({
    x: 0,
    y: 80,
    rotation: 0,
    scale: 1.0,
    prompt: "a photo of a car",
    steps: 20,
    guidance: 7.5,
    seed: 42
  });

  // Check server health
  useEffect(() => {
    fetch('http://localhost:8000/')
      .then(res => res.json())
      .then(data => setServerStatus(data.model_loaded ? "Ready" : "Model Error"))
      .catch(() => setServerStatus("Disconnected"));
  }, []);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null); // Reset result when new image loaded
    }
  };

  const handleChange = (e) => {
    setParams({ ...params, [e.target.name]: e.target.value });
  };

  const handleGenerate = async () => {
    if (!image) return alert("Please upload a license plate image first!");
    
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', image);
    Object.keys(params).forEach(key => formData.append(key, params[key]));

    try {
      const response = await fetch('http://localhost:8000/generate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error("Server error");

      const blob = await response.blob();
      setResult(URL.createObjectURL(blob));
    } catch (error) {
      console.error(error);
      alert("Failed to generate image. Is the Docker backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header>
        <h1>Generator</h1>
        <span className="status">Server: {serverStatus}</span>
      </header>

      <div className="main-layout">
        {/* LEFT PANEL: CONTROLS */}
        <div className="panel controls">
          <div className="upload-section">
            <label className="custom-file-upload">
              Upload Plate Image
              <input type="file" accept="image/*" onChange={handleImageChange} />
            </label>
          </div>

          <div className="form-group">
            <label>Prompt</label>
            <textarea name="prompt" rows="3" value={params.prompt} onChange={handleChange} />
          </div>

          <div className="sliders">
            <div className="slider-group">
              <label>Position X: {params.x}</label>
              <input type="range" name="x" min="-200" max="200" value={params.x} onChange={handleChange} />
            </div>
            <div className="slider-group">
              <label>Position Y: {params.y}</label>
              <input type="range" name="y" min="-200" max="200" value={params.y} onChange={handleChange} />
            </div>
            <div className="slider-group">
              <label>Rotation: {params.rotation}°</label>
              <input type="range" name="rotation" min="-45" max="45" value={params.rotation} onChange={handleChange} />
            </div>
            <div className="slider-group">
              <label>Scale: {params.scale}x</label>
              <input type="range" name="scale" min="0.5" max="2.0" step="0.1" value={params.scale} onChange={handleChange} />
            </div>
          </div>

          <details>
            <summary>Advanced Settings</summary>
            <div className="slider-group">
              <label>Steps: {params.steps}</label>
              <input type="range" name="steps" min="10" max="50" value={params.steps} onChange={handleChange} />
            </div>
            <div className="slider-group">
              <label>Guidance: {params.guidance}</label>
              <input type="range" name="guidance" min="1" max="15" step="0.5" value={params.guidance} onChange={handleChange} />
            </div>
            <div className="slider-group">
              <label>Seed: {params.seed}</label>
              <input type="number" name="seed" value={params.seed} onChange={handleChange} />
            </div>
          </details>

          <button className="generate-btn" onClick={handleGenerate} disabled={loading || !image}>
            {loading ? "Generating..." : "Generate Car"}
          </button>
        </div>

        {/* RIGHT PANEL: PREVIEW */}
        <div className="panel preview-area">
          <div className="canvas-wrapper">
            <h3>Live Preview</h3>
            <div className="canvas">
              {previewUrl && (
                <img 
                  src={previewUrl} 
                  className="plate-preview"
                  style={{
                    transform: `translate(-50%, -50%) translate(${params.x}px, ${params.y}px) rotate(${params.rotation}deg) scale(${params.scale})`
                  }}
                  alt="Plate"
                />
              )}
              {!previewUrl && <div className="placeholder">Upload an image to start</div>}
            </div>
          </div>

          <div className="result-wrapper">
            <h3>Result</h3>
            {result ? (
              <img src={result} className="result-img" alt="Result" />
            ) : (
              <div className="placeholder result-placeholder">
                {loading ? <div className="loader"></div> : "AI Output will appear here"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;