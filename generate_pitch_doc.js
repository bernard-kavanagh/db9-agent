"use strict";

const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  PageSize,
  PageOrientation,
  Header,
  Footer,
  PageNumber,
  NumberFormat,
  TableOfContents,
  ShadingType,
  BorderStyle,
  WidthType,
  Table,
  TableRow,
  TableCell,
  VerticalAlign,
  Tab,
  TabStopType,
  TabStopLeader,
} = require("docx");
const fs = require("fs");

// ─── Colour palette ──────────────────────────────────────────────────────────
const NAVY      = "1e3a5f";   // headings
const ORANGE    = "c45000";   // stage directions
const GREY_TEXT = "6b6b6b";   // speaker notes
const CODE_BG   = "f0f0f0";   // code block shading
const DIVIDER   = "c8d4e0";   // horizontal-ish tint
const WHITE     = "FFFFFF";

// ─── Helper: blank line ───────────────────────────────────────────────────────
function blank(spacing = 120) {
  return new Paragraph({ spacing: { before: spacing, after: 0 } });
}

// ─── Helper: thin divider paragraph (left-border style) ──────────────────────
function divider() {
  return new Paragraph({
    border: {
      bottom: { color: DIVIDER, size: 6, style: BorderStyle.SINGLE },
    },
    spacing: { before: 200, after: 200 },
  });
}

// ─── Helper: section heading (navy, bold, caps) ───────────────────────────────
function sectionHeading(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text: text.toUpperCase(),
        bold: true,
        color: NAVY,
        size: 28,          // 14pt
        font: "Calibri",
        allCaps: true,
        characterSpacing: 40,
      }),
    ],
    spacing: { before: 400, after: 120 },
    border: {
      bottom: { color: NAVY, size: 8, style: BorderStyle.SINGLE },
    },
  });
}

// ─── Helper: sub-heading (navy, bold) ────────────────────────────────────────
function subHeading(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text,
        bold: true,
        color: NAVY,
        size: 24,          // 12pt
        font: "Calibri",
      }),
    ],
    spacing: { before: 280, after: 80 },
  });
}

// ─── Helper: stage direction (orange italic) ──────────────────────────────────
function stageDirection(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text: `[${text}]`,
        italics: true,
        color: ORANGE,
        size: 20,          // 10pt
        font: "Calibri",
        bold: true,
      }),
    ],
    spacing: { before: 80, after: 80 },
  });
}

// ─── Helper: speaker note (grey italic) ──────────────────────────────────────
function speakerNote(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text: `Speaker note: ${text}`,
        italics: true,
        color: GREY_TEXT,
        size: 18,          // 9pt
        font: "Calibri",
      }),
    ],
    indent: { left: 360 },
    spacing: { before: 80, after: 80 },
    border: {
      left: { color: "cccccc", size: 12, style: BorderStyle.SINGLE },
    },
  });
}

// ─── Helper: "when to use" label ─────────────────────────────────────────────
function whenToUse(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text: "When to use: ",
        bold: true,
        color: GREY_TEXT,
        size: 18,
        font: "Calibri",
        italics: true,
      }),
      new TextRun({
        text,
        color: GREY_TEXT,
        size: 18,
        font: "Calibri",
        italics: true,
      }),
    ],
    spacing: { before: 60, after: 140 },
  });
}

// ─── Helper: body paragraph ──────────────────────────────────────────────────
function body(text, { bold = false } = {}) {
  return new Paragraph({
    children: [
      new TextRun({
        text,
        bold,
        size: 22,          // 11pt
        font: "Calibri",
        color: "1a1a1a",
      }),
    ],
    spacing: { before: 80, after: 80 },
    alignment: AlignmentType.JUSTIFIED,
  });
}

// ─── Helper: speech / dialogue line ──────────────────────────────────────────
function speech(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text: `"${text}"`,
        size: 22,
        font: "Calibri",
        color: "1a1a1a",
        italics: false,
      }),
    ],
    spacing: { before: 80, after: 80 },
    indent: { left: 360 },
    alignment: AlignmentType.JUSTIFIED,
    border: {
      left: { color: NAVY, size: 14, style: BorderStyle.SINGLE },
    },
  });
}

// ─── Helper: code block ──────────────────────────────────────────────────────
function codeBlock(lines) {
  const paragraphs = [];
  const linesArray = Array.isArray(lines) ? lines : [lines];
  linesArray.forEach((line, i) => {
    paragraphs.push(
      new Paragraph({
        children: [
          new TextRun({
            text: line || " ",
            font: "Courier New",
            size: 18,
            color: "1a1a1a",
          }),
        ],
        spacing: { before: i === 0 ? 80 : 0, after: 0 },
        indent: { left: 240, right: 240 },
        shading: {
          type: ShadingType.SOLID,
          color: CODE_BG,
          fill: CODE_BG,
        },
        border:
          i === 0
            ? {
                top:   { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
                left:  { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
                right: { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
              }
            : i === linesArray.length - 1
            ? {
                bottom: { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
                left:   { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
                right:  { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
              }
            : {
                left:  { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
                right: { color: "cccccc", size: 4, style: BorderStyle.SINGLE },
              },
      })
    );
  });
  return paragraphs;
}

// ─── Helper: bullet point ────────────────────────────────────────────────────
function bullet(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text,
        size: 22,
        font: "Calibri",
        color: "1a1a1a",
      }),
    ],
    bullet: { level: 0 },
    spacing: { before: 40, after: 40 },
  });
}

// ─── Helper: objection block ─────────────────────────────────────────────────
function objection(question, answer) {
  return [
    new Paragraph({
      children: [
        new TextRun({
          text: question,
          bold: true,
          size: 22,
          font: "Calibri",
          color: NAVY,
          italics: true,
        }),
      ],
      spacing: { before: 220, after: 60 },
    }),
    new Paragraph({
      children: [
        new TextRun({
          text: answer,
          size: 22,
          font: "Calibri",
          color: "1a1a1a",
        }),
      ],
      spacing: { before: 0, after: 80 },
      alignment: AlignmentType.JUSTIFIED,
    }),
  ];
}

// ═══════════════════════════════════════════════════════════════════════════════
//  BUILD DOCUMENT
// ═══════════════════════════════════════════════════════════════════════════════
const doc = new Document({
  // Footer repeated on every page
  sections: [
    // ── TITLE PAGE ──────────────────────────────────────────────────────────
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4 in twips
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: "db9.ai — Confidential   |   ",
                  size: 16,
                  font: "Calibri",
                  color: GREY_TEXT,
                }),
                new TextRun({
                  children: [PageNumber.CURRENT],
                  size: 16,
                  font: "Calibri",
                  color: GREY_TEXT,
                }),
              ],
              alignment: AlignmentType.RIGHT,
            }),
          ],
        }),
      },
      children: [
        // Big vertical space to push title down
        ...Array(10).fill(null).map(() => blank(200)),

        new Paragraph({
          children: [
            new TextRun({
              text: "db9.ai",
              bold: true,
              size: 96,       // 48pt
              font: "Calibri",
              color: NAVY,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 160 },
        }),

        new Paragraph({
          children: [
            new TextRun({
              text: "Pitch & Demo Scripts — EMEA Outreach",
              size: 36,       // 18pt
              font: "Calibri",
              color: GREY_TEXT,
              italics: true,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 240 },
        }),

        divider(),

        new Paragraph({
          children: [
            new TextRun({
              text: "March 2026",
              size: 24,
              font: "Calibri",
              color: GREY_TEXT,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { before: 200, after: 0 },
        }),

        // Push to bottom of title page
        ...Array(15).fill(null).map(() => blank(200)),

        new Paragraph({
          children: [
            new TextRun({
              text: "CONFIDENTIAL — For internal use only",
              size: 18,
              font: "Calibri",
              color: GREY_TEXT,
              italics: true,
            }),
          ],
          alignment: AlignmentType.CENTER,
        }),
      ],
    },

    // ── CONTENT SECTION ──────────────────────────────────────────────────────
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4
          margin: { top: 1080, bottom: 1080, left: 1200, right: 1200 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: "db9.ai — Confidential   |   Page ",
                  size: 16,
                  font: "Calibri",
                  color: GREY_TEXT,
                }),
                new TextRun({
                  children: [PageNumber.CURRENT],
                  size: 16,
                  font: "Calibri",
                  color: GREY_TEXT,
                }),
                new TextRun({
                  text: " of ",
                  size: 16,
                  font: "Calibri",
                  color: GREY_TEXT,
                }),
                new TextRun({
                  children: [PageNumber.TOTAL_PAGES],
                  size: 16,
                  font: "Calibri",
                  color: GREY_TEXT,
                }),
              ],
              alignment: AlignmentType.RIGHT,
            }),
          ],
        }),
      },
      children: [

        // ────────────────────────────────────────────────────────────────────
        //  SECTION 1 — ELEVATOR PITCH
        // ────────────────────────────────────────────────────────────────────
        sectionHeading("Section 1: Elevator Pitch — 30 Seconds"),
        whenToUse("Cold intro, LinkedIn message follow-up, first 30 seconds of a call"),
        blank(80),

        speech("You're building with AI agents — which means your agents need memory, storage, and the ability to query data. Right now most teams are stitching together Postgres, S3, and a vector database separately."),
        blank(60),
        speech("db9 is a single serverless database built specifically for AI agents — you get full Postgres, file storage, and vector search in one place, spun up in seconds with one CLI command. No config, no infrastructure overhead."),
        blank(60),
        speech("We're talking to AI-first teams in Europe right now. Would it be worth 20 minutes to show you what it looks like?"),
        blank(80),

        speakerNote("Pause after \"separately\" — let the pain land. Adjust the opening line based on what you know about their stack."),

        divider(),

        // ────────────────────────────────────────────────────────────────────
        //  SECTION 2 — FULL PITCH SCRIPT
        // ────────────────────────────────────────────────────────────────────
        sectionHeading("Section 2: Full Pitch Script — 5–7 Minutes"),
        whenToUse("Intro call, demo introduction, investor meeting"),
        blank(80),

        // — Opening
        subHeading("Opening — The Problem (60 seconds)"),
        speech("Let me start with something I'm seeing across AI teams in Europe right now."),
        blank(40),
        speech("You're building an agent — maybe a copilot, an automation workflow, a research agent. And at some point you hit the same wall: your agent needs to remember things. It needs to store structured data, retrieve context, maybe store documents or transcripts."),
        blank(40),
        speech("So what happens? You spin up a Postgres database. Then you add S3 for file storage. Then you realise you need vector search, so you bolt on pgvector or Pinecone. Then you need to schedule some recurring tasks, so you add a cron service."),
        blank(40),
        speech("Before you know it, you've got four pieces of infrastructure to manage — and you haven't shipped anything yet."),
        blank(60),
        stageDirection("Pause"),
        blank(40),
        speech("That's the problem db9 solves."),
        blank(80),

        // — Solution
        subHeading("The Solution (60 seconds)"),
        speech("db9 is serverless Postgres built specifically for AI agents."),
        blank(40),
        speech("It combines a full PostgreSQL database with cloud file storage, vector search, HTTP calls from SQL, and built-in cron scheduling — all in one place. One connection string. One CLI. Zero configuration."),
        blank(40),
        speech("You run one command: db9 db create --name myapp — and in seconds you have a production-grade database with all of those capabilities ready to go."),
        blank(40),
        speech("The tagline is: Postgres but for agents. SQL when you need power. File ops when you need simplicity."),
        blank(80),

        // — Why it matters
        subHeading("Why It Matters for AI Agents (90 seconds)"),
        speech("Think about the three most common agent patterns we see:"),
        blank(40),
        speech("First — personal assistants and copilots. Your agent needs structured memory — what did the user ask last week, what are their preferences. That goes in Postgres tables. But it also needs to store raw conversation transcripts and documents. That goes in the filesystem. With db9, both live in the same place."),
        blank(40),
        speech("Second — research and coding agents. Your agent is pulling in source documents, chunking them, generating embeddings. With db9, the source files live in the filesystem, and the chunks, metadata, and vectors are in Postgres with pgvector. No separate vector database needed."),
        blank(40),
        speech("Third — multi-agent automation. Each run produces reports and artifacts. db9 stores the files, and the run history and metadata stay in Postgres. Your orchestration layer can query across everything with SQL."),
        blank(80),

        // — Developer experience
        subHeading("The Developer Experience (60 seconds)"),
        speech("What we've really focused on is developer experience."),
        blank(40),
        speech("Type generation from your schema in one command — TypeScript or Python. Environment branching — you can clone an entire database including tables, files, cron jobs, and permissions to create an isolated test environment. Built-in observability — query latency, slow queries, connection tracking."),
        blank(40),
        speech("And it works with every agent framework — Claude, OpenAI, Cursor, Cline, any Postgres-compatible driver."),
        blank(80),

        // — The ask
        subHeading("The Ask (30 seconds)"),
        speech("We're specifically talking to AI-first teams in Europe right now — companies building agents, copilots, and autonomous systems."),
        blank(40),
        speech("I'd love to show you a live demo — it takes about 15 minutes and I'll show you the CLI, a real agent workflow, and the vector search in action."),
        blank(40),
        speech("Does that sound useful?"),
        blank(80),

        divider(),

        // ────────────────────────────────────────────────────────────────────
        //  SECTION 3 — DEMO SCRIPT
        // ────────────────────────────────────────────────────────────────────
        sectionHeading("Section 3: Demo Script — 15–20 Minutes"),
        whenToUse("After the pitch, on a screen share"),
        blank(60),

        subHeading("Setup Required Before the Call"),
        bullet("db9 CLI installed and logged in"),
        bullet("Terminal open in a clean working directory"),
        bullet("Browser tab open at db9.ai"),
        bullet("Have a simple Python agent script ready"),
        blank(80),

        // Step 1
        subHeading("Step 1 — Spin Up a Database (2 minutes)"),
        speech("Let me show you how fast this is."),
        stageDirection("Open terminal"),
        speech("I'm going to create a brand new database right now."),
        stageDirection("Type the following command"),
        ...codeBlock(["db9 db create --name demo-agent"]),
        blank(60),
        speech("That's it. I now have a full Postgres database with all the extensions ready — vector search, file storage, HTTP calls, cron scheduling. One command."),
        stageDirection("Type the following command"),
        ...codeBlock(["db9 db list"]),
        blank(60),
        speech("Here's our connection string. I can hand this to any Postgres driver, any ORM, psql — it just works."),
        blank(60),
        speakerNote("Comment on the speed — it usually takes 2–3 seconds. That moment lands well."),
        blank(80),

        // Step 2
        subHeading("Step 2 — Show the Filesystem (3 minutes)"),
        speech("Now let me show you something that isn't in standard Postgres."),
        blank(40),
        speech("Every db9 database comes with a cloud filesystem alongside the relational database. So I can do this:"),
        stageDirection("Type the following commands"),
        ...codeBlock([
          'echo "Meeting transcript: discussed Q2 roadmap..." > transcript.txt',
          "db9 fs upload transcript.txt /transcripts/transcript.txt",
          "db9 fs ls /transcripts/",
        ]),
        blank(60),
        speech("I've just stored a file in my database's filesystem. Now watch this — I can query that file with SQL:"),
        stageDirection("Type the following command"),
        ...codeBlock([
          "db9 sql \"SELECT * FROM fs9.read_text('/transcripts/transcript.txt')\"",
        ]),
        blank(60),
        speech("SQL and file ops, unified. For an AI agent, this is huge — you store your structured data in tables and your raw documents, transcripts, and artifacts in the filesystem. One connection string for both."),
        blank(80),

        // Step 3
        subHeading("Step 3 — Vector Search (4 minutes)"),
        speech("Now let's talk about the thing every AI team needs — vector search."),
        blank(40),
        speech("Most teams add Pinecone or a separate pgvector instance. With db9 it's built in."),
        stageDirection("Type the following commands"),
        ...codeBlock([
          "db9 sql \"CREATE TABLE documents (id SERIAL PRIMARY KEY, content TEXT, embedding VECTOR(1536));\"",
          "",
          "db9 sql \"INSERT INTO documents (content, embedding) VALUES ('db9 is serverless postgres for AI agents', '[0.1, 0.2, ...]');\"",
          "",
          "db9 sql \"SELECT content, embedding <=> '[0.1, 0.21, ...]' AS distance FROM documents ORDER BY distance LIMIT 5;\"",
        ]),
        blank(60),
        speech("Cosine similarity, L2 distance, inner product — all standard pgvector syntax. Your RAG pipeline just became a SQL query."),
        blank(60),
        speakerNote("If they're using a specific vector DB, call it out — \"So if you're using Pinecone today, this replaces that entirely.\""),
        blank(80),

        // Step 4
        subHeading("Step 4 — HTTP Calls from SQL (3 minutes)"),
        speech("Here's one that surprises people. You can make HTTP calls from inside a SQL query."),
        stageDirection("Type the following command"),
        ...codeBlock([
          "db9 sql \"SELECT http_get('https://api.exchangeratesapi.io/latest?base=USD');\"",
        ]),
        blank(60),
        speech("Your agent can call external APIs, enrich data, trigger webhooks — all from SQL. No middleware, no separate service."),
        blank(60),
        speakerNote("Tailor the API example to their domain if you know it — fintech, HR data, etc."),
        blank(80),

        // Step 5
        subHeading("Step 5 — Environment Branching (2 minutes)"),
        speech("Last thing — branching. This is huge for teams."),
        stageDirection("Type the following command"),
        ...codeBlock(["db9 db branch --name demo-agent-staging"]),
        blank(60),
        speech("I've just cloned the entire database — tables, files, cron jobs, permissions — into a staging environment. My agents can test against production-like data without touching production."),
        blank(40),
        speech("When I'm done I just delete the branch. No cleanup scripts."),
        blank(80),

        // Closing
        subHeading("Closing the Demo (2 minutes)"),
        speech("So that's db9 in about 15 minutes — database creation, unified filesystem, vector search, HTTP from SQL, and branching."),
        blank(40),
        speech("The thing I want to leave you with is this: the complexity tax of stitching together four pieces of infrastructure is real. It slows you down before you've shipped anything."),
        blank(40),
        speech("db9 removes that tax. One database, everything your agent needs."),
        blank(40),
        speech("Two questions for you — does this match the infrastructure problem you're dealing with? And what does your current stack look like for agent memory and storage?"),
        blank(60),
        speakerNote("Shut up after the questions. Let them talk. Their answer tells you exactly how to position the next conversation."),
        blank(80),

        divider(),

        // ────────────────────────────────────────────────────────────────────
        //  SECTION 4 — OBJECTION HANDLING
        // ────────────────────────────────────────────────────────────────────
        sectionHeading("Section 4: Objection Handling"),
        blank(40),

        ...objection(
          '"We already use Postgres + pgvector, it\'s fine"',
          "That's a great starting point — db9 is fully Postgres compatible so migration is zero friction. The difference is the file storage and the operational overhead. You'd keep all your existing queries and just remove the S3 bucket and the cron service."
        ),

        ...objection(
          '"We\'re happy with Pinecone / Supabase / PlanetScale"',
          "Totally understand — the question is whether having vector search, file storage, and relational data in one place would reduce your infrastructure complexity. A lot of teams we talk to are maintaining 3 services when they could have 1."
        ),

        ...objection(
          '"Is it production ready?"',
          "Full PostgreSQL compatibility — 600+ ORM tests passing. Built-in observability, connection pooling, branching for staging environments. Teams are running it in production today."
        ),

        ...objection(
          '"What does it cost?"',
          "Serverless pricing — you pay for what you use. Happy to run through numbers based on your expected workload on a follow-up call."
        ),

        ...objection(
          '"We have an in-house DBA / infrastructure team"',
          "Then this frees them up from routine provisioning and lets them focus on higher-value work. Branching in particular tends to resonate with infra teams — cloning an environment for testing with one command."
        ),

        blank(200),
        divider(),

        new Paragraph({
          children: [
            new TextRun({
              text: "db9.ai — Confidential — March 2026",
              size: 16,
              font: "Calibri",
              color: GREY_TEXT,
              italics: true,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { before: 200, after: 0 },
        }),
      ],
    },
  ],
});

// ─── Write file ───────────────────────────────────────────────────────────────
Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(
    "/Users/bernardkavanagh/db9_agent/DB9_PITCH_AND_DEMO_SCRIPTS.docx",
    buffer
  );
  console.log("Document saved successfully.");
});
