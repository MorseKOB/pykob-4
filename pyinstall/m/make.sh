#!/bin/sh

# MIT License
# 
# Copyright (c) 2020 PyKOB - MorseKOB in Python
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

echo "Make the Mac bundle"

# Remove any existing build and dist folders
if [ -d "build" ]; then rm -Rf build; fi
if [ -d "dist" ]; then rm -Rf dist; fi

# Build Configure.exe
echo "Building Configure..."
python3 -m PyInstaller --clean --log-level INFO --workpath=build --distpath=distC Configure.spec
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error generating Command.exe: $retVal"
    exit $retVal
fi

# Build MKOB.exe
echo "Building MKOB..."
python3 -m PyInstaller --clean --log-level INFO --workpath=build --distpath=distM MKOB.spec
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error generating MKOB.exe: $retVal"
    exit $retVal
fi

# Copy Configure.exe into the dist/MKOB folder so they can be packaged together.
echo "Copy Configure into dist/MKOB folder..."
cp distC/Configure/Configure distM/MKOB
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error copying Configure into MKOB: $retVal"
    exit $retVal
fi

# Generate the zip file.
echo "Create MKOB.zip..."
zip -r distM/MKOB-Mac.zip distM/MKOB/*
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error creating ZIP of MKOB: $retVal"
    exit $retVal
fi

echo "MKOB built and ZIP created."
exit 0
