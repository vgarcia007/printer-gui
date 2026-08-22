# Third-party software

Print & Scan Hub is GPL-3.0 software. Container images also install or download third-party components under their respective licenses.

- Bootstrap assets are distributed under the MIT License.
- The CUPS image is based on olbat/cupsd and includes CUPS and Debian printer drivers.
- printer-driver-dymo provides the DYMO LabelWriter driver.
- HP Unified Linux Driver components are downloaded from HP during the build, checksum-verified, and are not stored in this repository. HP's license terms apply.
- Brother brscan4 is downloaded from Brother during the scanner image build, checksum-verified, and is not stored in this repository. Brother's license terms apply.
- OCRmyPDF and Tesseract provide OCR processing; English and German language data comes from Debian.
- The front/back page ordering and recovery workflow was informed by the MIT-licensed BrotherScannerDocker project. Its PHP interface, uploads, notification integrations, device-button handlers, and Git history were not imported.

Consult the installed package copyright files in each image for authoritative license texts.
