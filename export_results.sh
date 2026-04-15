#!/bin/bash

# Export BTCUSD Trading Results from WSL to Windows
# Bash script to copy results and optionally open in browser

SOURCE_PATH="/home/user/claudebtcusdtrdpm/btcusd-trader/results"
DEST_PATH="/mnt/c/Users/admin/claudebtcusdtrdpm/results"
OPEN_BROWSER=${1:-true}

# Create destination folder if it doesn't exist
if [ ! -d "$DEST_PATH" ]; then
    echo "📁 Creating folder: $DEST_PATH"
    mkdir -p "$DEST_PATH"
fi

# Copy HTML files
echo "📋 Copying files..."
file_count=0

for file in "$SOURCE_PATH"/*.html; do
    if [ -f "$file" ]; then
        cp "$file" "$DEST_PATH/"
        echo "  ✅ $(basename "$file")"
        ((file_count++))
    fi
done

# Copy JSON files
for file in "$SOURCE_PATH"/*.json; do
    if [ -f "$file" ]; then
        cp "$file" "$DEST_PATH/"
        echo "  ✅ $(basename "$file")"
        ((file_count++))
    fi
done

# Copy CSV files
for file in "$SOURCE_PATH"/*.csv; do
    if [ -f "$file" ]; then
        cp "$file" "$DEST_PATH/"
        echo "  ✅ $(basename "$file")"
        ((file_count++))
    fi
done

if [ $file_count -eq 0 ]; then
    echo "⚠️  No files found to copy"
    exit 1
fi

echo "✅ $file_count files copied successfully!"

# Open report in browser if requested (and wslview is available)
if [ "$OPEN_BROWSER" = "true" ] && command -v wslview &> /dev/null; then
    REPORT_PATH="$DEST_PATH/mt4_report.html"
    if [ -f "$REPORT_PATH" ]; then
        echo "🌐 Opening report in browser..."
        wslview "$REPORT_PATH" &
        echo "✅ Report opened!"
    fi
fi

echo ""
echo "📊 Results available at:"
echo "   Windows: C:\Users\admin\claudebtcusdtrdpm\results"
echo "   WSL:     $DEST_PATH"
