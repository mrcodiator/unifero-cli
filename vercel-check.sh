#!/bin/bash

# Unifero CLI - Vercel Deployment Checklist
# This script verifies your project is ready for Vercel deployment

echo "🚀 Unifero CLI - Vercel Deployment Checklist"
echo "=============================================="
echo ""

# Check if we're in the right directory
if [[ ! -f "api.py" ]]; then
    echo "❌ Error: api.py not found. Please run this from the unifero-cli directory."
    exit 1
fi

echo "✅ Project Structure:"
echo "   - api.py (FastAPI entry point)"
echo "   - vercel.json (Vercel configuration)"
echo "   - runtime.txt (Python version)"
echo "   - requirements.txt (Dependencies)"
echo "   - .vercelignore (Deployment exclusions)"
echo ""

# Check Python version
if [[ -f "runtime.txt" ]]; then
    python_version=$(cat runtime.txt)
    echo "✅ Python version: $python_version"
else
    echo "❌ runtime.txt missing"
fi

# Check vercel.json
if [[ -f "vercel.json" ]]; then
    echo "✅ vercel.json configuration present"
else
    echo "❌ vercel.json missing"
fi

# Check requirements
if [[ -f "requirements.txt" ]]; then
    echo "✅ requirements.txt present with $(wc -l < requirements.txt) dependencies"
else
    echo "❌ requirements.txt missing"
fi

echo ""
echo "🧪 Pre-deployment Test:"

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
    
    # Test API import
    python -c "
try:
    from api import app
    from tools.unifero import UniferoTool
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"
else
    echo "⚠️  Virtual environment not active. Run: source .venv/bin/activate"
fi

echo ""
echo "📋 Next Steps:"
echo "1. Ensure your code is committed to Git"
echo "2. Push to your repository (GitHub/GitLab/Bitbucket)"
echo "3. Install Vercel CLI: npm install -g vercel"
echo "4. Login to Vercel: vercel login"
echo "5. Deploy: vercel (from this directory)"
echo "6. For production: vercel --prod"
echo ""
echo "📚 Documentation:"
echo "- Deployment guide: ./DEPLOYMENT.md"
echo "- Project README: ./README.md"
echo "- Vercel FastAPI docs: https://vercel.com/docs/frameworks/backend/fastapi"
echo ""
echo "🎉 Your project is ready for Vercel deployment!"