# 🚀 Vercel Deployment Guide for Unifero CLI API

## Quick Deployment Steps

### 1. Prerequisites

- [Vercel account](https://vercel.com)
- Git repository (GitHub/GitLab/Bitbucket)
- Vercel CLI: `npm install -g vercel`

### 2. Test Locally (Important!)

```bash
# Activate virtual environment
source .venv/bin/activate

# Test API functionality
python -c "
import requests
import time
import subprocess
from threading import Thread

def start_server():
    subprocess.run(['uvicorn', 'api:app', '--port', '8000'], cwd='.')

thread = Thread(target=start_server, daemon=True)
thread.start()
time.sleep(3)

try:
    response = requests.get('http://localhost:8000/health', timeout=5)
    print('✅ Health check:', response.json())

    test_data = {'mode': 'search', 'query': 'test', 'limit': 1}
    response = requests.post('http://localhost:8000/process', json=test_data, timeout=10)
    print('✅ Process endpoint: Status', response.status_code)
    print('🎉 API is ready for deployment!')
except Exception as e:
    print('❌ Error:', str(e))
"
```

### 3. Deploy to Vercel

```bash
# Login to Vercel (first time only)
vercel login

# Navigate to your project directory
cd /path/to/unifero-cli

# Deploy (will prompt for project settings)
vercel

# For production deployment
vercel --prod
```

### 4. Configuration Files

Your project includes these Vercel-ready files:

- ✅ `vercel.json` - Vercel configuration
- ✅ `runtime.txt` - Python 3.11 specification
- ✅ `requirements.txt` - Dependencies
- ✅ `.vercelignore` - Deployment exclusions

### 5. Test Your Deployed API

After deployment, Vercel will provide a URL like `https://your-app.vercel.app`

```bash
# Test health endpoint
curl https://your-app.vercel.app/health

# Test search functionality
curl -X POST https://your-app.vercel.app/process \
  -H "Content-Type: application/json" \
  -d '{"mode":"search","query":"Next.js routing","limit":2}'

# Test docs functionality
curl -X POST https://your-app.vercel.app/process \
  -H "Content-Type: application/json" \
  -d '{"mode":"docs","url":"https://nextjs.org/docs","limit":1}'
```

### 6. View API Documentation

- Interactive docs: `https://your-app.vercel.app/docs`
- Alternative docs: `https://your-app.vercel.app/redoc`

## Troubleshooting

### Common Issues:

1. **Module import errors**: Ensure all dependencies are in `requirements.txt`
2. **Timeout errors**: Vercel has 10s timeout - reduce content limits if needed
3. **Memory issues**: Use smaller search/docs limits for production

### Environment Variables:

If you need environment variables:

```bash
vercel env add VARIABLE_NAME production
```

### Logs and Monitoring:

- View function logs in Vercel dashboard
- Monitor performance and errors
- Set up alerts for failures

## Production Tips

1. **Performance**: Consider caching results for repeated queries
2. **Rate Limiting**: Add rate limiting for production use
3. **Error Handling**: Monitor error rates and timeouts
4. **Security**: Add API key authentication if needed

## Support

- Check Vercel docs: https://vercel.com/docs/frameworks/backend/fastapi
- FastAPI docs: https://fastapi.tiangolo.com/
- Project issues: [Your repository issues]

---

✨ Your Unifero CLI API is now ready for the world! 🌍
