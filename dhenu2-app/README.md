# Dhenu2 Farming AI — Node.js App

## Setup (One Time)

```
npm install
```

## Run

```
node server.js
```

Then open: http://localhost:3000

## Requirements

- Node.js 18+
- Ollama running: `ollama serve`
- Model loaded: `ollama run dhenu2-farming`

## API Endpoints

| Endpoint       | Method | Description                        |
|----------------|--------|------------------------------------|
| /api/chat      | POST   | Send message, get translated reply |
| /api/detect    | POST   | Detect language of text            |
| /api/health    | GET    | Check Ollama server status         |

## Change Model Name

In server.js line 12:
```js
const MODEL = 'dhenu2-farming';  // change to your ollama model name
```

## Languages Supported (Auto-detected)
Tamil · Telugu · Kannada · Malayalam · Hindi · Marathi · Bengali · Punjabi · English
