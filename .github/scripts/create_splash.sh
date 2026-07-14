#! /bin/sh
# ------------------------------------------------------------------
# Stamp the release version onto the committed, version-independent
# splash image.
#
#   Input:  ./images/splash/splash.webp          (version-less base)
#   Output: ./images/splash_with_version.webp    (base + version)
#
# Run at release time (scripts/release.py); needs a local ImageMagick.
# ------------------------------------------------------------------

# --- check imagemagick version ---
echo "------ ImageMagick version info --------------------------------------------"
magick identify -version
echo "----------------------------------------------------------------------------"

# --- argument handling ---
DISPLAY_VERSION="$1"  # e.g. "v1.5.0"

# --- credit the AI-generated background ---
magick -pointsize 48 -font "./images/splash/google_fonts_montserrat_italic.ttf" \
       "./images/splash/splash.webp" \
       -gravity SouthWest -fill "#aaaaaa" -annotate +10+5 "DiffusionBee 2.5.3 (FLUX.1-dev + Real-ESRGAN)" \
       "./images/temp.mpc"

# --- add version info (white text over a subtle black shadow) ---
magick -pointsize 128 -font "./images/splash/google_fonts_montserrat_bold.ttf" \
       "./images/temp.mpc" \
       -gravity West -fill "black" -annotate +598+203 "${DISPLAY_VERSION}" \
       "./images/temp.mpc"
magick -pointsize 128 -font "./images/splash/google_fonts_montserrat_bold.ttf" \
       "./images/temp.mpc" \
       -gravity West -fill "white" -annotate +595+200 "${DISPLAY_VERSION}" \
       -quality 95 -define webp:lossless=false \
       "./images/splash_with_version.webp"

# --- clean up ---
echo "Cleaning up..."
rm ./images/*.mpc
rm ./images/*.cache 2>/dev/null || true
