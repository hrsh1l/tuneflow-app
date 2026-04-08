import cors from "cors";
import express from "express";
import multer from "multer";
import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024,
  },
});

const app = express();
const port = Number(process.env.PORT || 5000);
const pythonBin = process.env.PYTHON_BIN || "python";
const ffmpegBin = process.env.FFMPEG_BIN || "ffmpeg";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

app.use(cors());
app.use(express.json());

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, log: "1-audio-upload" });
});

app.post("/api/analyze", upload.single("audioFile"), async (req, res) => {
  const youtubeUrl = req.body?.youtubeUrl?.trim();
  const uploadedFile = req.file;

  if (youtubeUrl) {
    return res.status(400).json({
      error: "Log 1 backend supports audio upload only. YouTube support is added in Log 2.",
    });
  }

  if (!uploadedFile) {
    return res.status(400).json({ error: "Please upload an audio file." });
  }

  const tempDirectory = await fs.mkdtemp(path.join(os.tmpdir(), "tuneflow-log1-"));

  try {
    const extension = path.extname(uploadedFile.originalname) || ".wav";
    const inputPath = path.join(tempDirectory, `upload${extension}`);
    await fs.writeFile(inputPath, uploadedFile.buffer);

    const wavPath = await convertAudioToWav(inputPath, tempDirectory);
    const analysis = await runAudioAnalysis(wavPath);

    return res.json({
      source: "upload",
      sourceInput: uploadedFile.originalname,
      ...analysis,
    });
  } catch (error) {
    return res.status(500).json({ error: error.message || "Analysis failed." });
  } finally {
    await fs.rm(tempDirectory, { recursive: true, force: true });
  }
});

async function runAudioAnalysis(audioPath) {
  const scriptPath = path.join(__dirname, "analyze_audio.py");

  try {
    const { stdout } = await execFileAsync(
      pythonBin,
      [scriptPath, "--input", audioPath],
      {
        timeout: 120000,
        windowsHide: true,
      },
    );

    return JSON.parse(stdout);
  } catch (error) {
    const stderrMessage = error.stderr?.trim();
    if (error.code === "ENOENT") {
      throw new Error(`Python executable not found: ${pythonBin}`);
    }

    throw new Error(stderrMessage || error.message || "Python analysis failed.");
  }
}

async function convertAudioToWav(inputPath, outputDirectory) {
  const outputPath = path.join(outputDirectory, "analysis.wav");
  const ffmpegArgs = [
    "-hide_banner",
    "-loglevel",
    "error",
    "-y",
    "-i",
    inputPath,
    "-vn",
    "-ac",
    "1",
    "-ar",
    "22050",
    "-c:a",
    "pcm_s16le",
    outputPath,
  ];

  const ffmpegCandidates = [ffmpegBin];
  const wingetFfmpeg = await resolveWingetFfmpegPath();
  if (wingetFfmpeg && !ffmpegCandidates.includes(wingetFfmpeg)) {
    ffmpegCandidates.push(wingetFfmpeg);
  }

  let notFoundCount = 0;

  for (const ffmpegExecutable of ffmpegCandidates) {
    try {
      await execFileAsync(ffmpegExecutable, ffmpegArgs, {
        timeout: 120000,
        windowsHide: true,
      });
      return outputPath;
    } catch (error) {
      if (error.code === "ENOENT") {
        notFoundCount += 1;
        continue;
      }

      throw new Error(error.stderr?.trim() || "Audio conversion to WAV failed.");
    }
  }

  if (notFoundCount > 0) {
    throw new Error(
      "ffmpeg is required for analysis preprocessing but was not found. Install ffmpeg, reopen your terminal, or set FFMPEG_BIN.",
    );
  }

  throw new Error("Audio conversion to WAV failed.");
}

async function resolveWingetFfmpegPath() {
  const localAppData = process.env.LOCALAPPDATA;
  if (!localAppData) {
    return "";
  }

  const packagesRoot = path.join(localAppData, "Microsoft", "WinGet", "Packages");

  try {
    const packageEntries = await fs.readdir(packagesRoot, { withFileTypes: true });
    const ffmpegPackage = packageEntries.find(
      (entry) => entry.isDirectory() && entry.name.startsWith("Gyan.FFmpeg_"),
    );

    if (!ffmpegPackage) {
      return "";
    }

    const ffmpegPackageRoot = path.join(packagesRoot, ffmpegPackage.name);
    const buildEntries = await fs.readdir(ffmpegPackageRoot, { withFileTypes: true });
    const ffmpegBuild = buildEntries.find(
      (entry) => entry.isDirectory() && entry.name.startsWith("ffmpeg-"),
    );

    if (!ffmpegBuild) {
      return "";
    }

    const ffmpegPath = path.join(ffmpegPackageRoot, ffmpegBuild.name, "bin", "ffmpeg.exe");
    await fs.access(ffmpegPath);
    return ffmpegPath;
  } catch {
    return "";
  }
}

app.listen(port, () => {
  console.log(`TuneFlow log1 backend listening at http://localhost:${port}`);
});
