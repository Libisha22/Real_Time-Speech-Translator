const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const original = document.getElementById('original');
const translated = document.getElementById('translated');
const targetLang = document.getElementById('targetLang');

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
  alert('Your browser does not support Speech Recognition.');
}

const recognition = new SpeechRecognition();
recognition.lang = 'en-US';
recognition.interimResults = false;

let finalText = '';

startBtn.onclick = () => {
  original.textContent = '';
  translated.textContent = '';
  finalText = '';
  recognition.start();
  startBtn.disabled = true;
  stopBtn.disabled = false;
};

stopBtn.onclick = () => {
  recognition.stop(); // triggers recognition.onend
  startBtn.disabled = false;
  stopBtn.disabled = true;
};

recognition.onresult = (event) => {
  finalText = event.results[0][0].transcript;
  original.textContent = finalText;
};

recognition.onend = async () => {
  if (!finalText) return;

  try {
    const response = await fetch('http://localhost:5000/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        q: finalText,
        source: 'en',
        target: targetLang.value,
        format: 'text'
      })
    });
    const data = await response.json();
    translated.textContent = data.translatedText;
  } catch (error) {
    translated.textContent = 'Translation failed.';
    console.error(error);
  }
};

recognition.onerror = (event) => {
  alert('Error: ' + event.error);
  startBtn.disabled = false;
  stopBtn.disabled = true;
};
