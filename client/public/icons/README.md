# PWA Icons Generation

This folder contains tools to generate all required PWA icons for Android installation.

## 📋 Required Icons

Your PWA needs these icon sizes:
- `icon-72.png` (72x72)
- `icon-96.png` (96x96)
- `icon-128.png` (128x128)
- `icon-144.png` (144x144)
- `icon-152.png` (152x152)
- `icon-192.png` (192x192) - **Required for Android**
- `icon-384.png` (384x384)
- `icon-512.png` (512x512) - **Required for Android**

## 🎨 Method 1: Browser-Based Generator (No Setup)

**Easiest method - No dependencies required!**

1. Open `generate-icons.html` in any web browser
2. Click "Generate All Icons"
3. Download each icon (right-click → Save image as...)
4. Save them in this folder with exact filenames

This creates simple placeholder icons with "I" letter.
**Replace with your actual logo later!**

## 🖼️ Method 2: Command-Line Generator (Custom Logo)

**For professional icons from your logo:**

### Prerequisites
- Node.js installed
- Your logo as `source-icon.png` (1024x1024 recommended)

### Steps

```bash
# 1. Place your logo in this folder
# Name it: source-icon.png
# Format: PNG with transparency (recommended)
# Size: 1024x1024 or larger, square

# 2. Install dependencies
npm install

# 3. Generate all icons
npm run generate-icons
```

This will create all 8 icon files from your source image.

## 🎯 Method 3: Design Tools

Use any image editor (Photoshop, GIMP, Figma, etc.):

1. Create/open your logo
2. Export these sizes:
   - 72x72, 96x96, 128x128, 144x144
   - 152x152, 192x192, 384x384, 512x512
3. Name them: `icon-{size}.png`
4. Save in this folder

## ✅ Verification

After generating icons, check:

```bash
# List all icons
ls -la icon-*.png

# Should see 8 files:
# icon-72.png
# icon-96.png
# icon-128.png
# icon-144.png
# icon-152.png
# icon-192.png
# icon-384.png
# icon-512.png
```

## 🚀 Next Steps

1. **Generate icons** (choose method above)
2. **Build app**: `npm run build` (in project root)
3. **Deploy**: Upload `dist/public/` to HTTPS server
4. **Test**: Open in Chrome on Android

## 📐 Design Guidelines

### Best Practices
- Square aspect ratio (1:1)
- Minimum 512x512 source image
- PNG format with transparency
- Simple, recognizable design
- Works on dark and light backgrounds

### Avoid
- Text (may be unreadable at small sizes)
- Complex details (simplify for 72x72)
- Landscape/portrait shapes (use square)
- Low-resolution source images

### Icon Composition
- **Safe Area**: Keep important content in center 80%
- **Padding**: Leave 10% padding around edges
- **Maskable**: Design works when circular mask applied

## 🎨 Design Tips

```
┌─────────────────┐
│  10% padding    │
│  ┌───────────┐  │
│  │           │  │
│  │   Logo    │  │  ← Keep logo in center 80%
│  │           │  │
│  └───────────┘  │
│  10% padding    │
└─────────────────┘
```

## 🔄 Updating Icons

To update icons after changes:

1. Replace `source-icon.png` with new version
2. Run `npm run generate-icons` again
3. Rebuild app: `npm run build`
4. Deploy updated `dist/public/` folder

## 🆘 Troubleshooting

### Icons not showing in installed app?
- Check filenames match exactly (lowercase)
- Verify all 8 files exist
- Rebuild app after adding icons
- Clear browser cache and reinstall

### Generator script fails?
- Ensure Node.js is installed
- Run `npm install` first
- Check `source-icon.png` exists
- Try browser-based generator instead

### Need help?
See main PWA documentation:
- `../../../PWA_IMPLEMENTATION_GUIDE.md`
- `../../../PWA_CHECKLIST.md`

---

**Quick Start**: Open `generate-icons.html` in browser → Generate → Download → Build app
