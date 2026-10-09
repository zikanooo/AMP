import re
import sys

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    print(f"Original length: {len(html)}")

    # 1. Update branding: "Open Motion" -> "Motion" in user-facing UI and wordmarks
    # Replace wordmark in home header
    html = html.replace('<div class="homeWordmark"><b>Open Motion</b></div>', '<div class="homeWordmark"><b>Motion</b></div>')
    html = html.replace('aria-label="Open Motion"', 'aria-label="Motion"')
    html = html.replace('title="Instal Open Motion"', 'title="Instal Motion"')
    html = html.replace('aria-label="Instal Open Motion"', 'aria-label="Instal Motion"')

    # 2. In homeTopActions: Clean up and simplify the top right corner!
    # User said: "hapus fitur preset demo anj dipojok kanan atas ... intinya simple halaman import aja tanpa ada pilihan resolver paket"
    # Replace the cluttered buttons with clean "IMPOR PRESET" button + Language button
    old_top_actions_pattern = r'<div class="homeTopActions">[\s\S]*?</div>\s*</header>'
    new_top_actions = """<div class="homeTopActions">
        <button id="homeAMLink" class="rightBtn motionImportBtn" type="button" title="Impor Preset Alight Motion / XML">
          <svg viewBox="0 0 24 24" fill="none" stroke="#00E599" stroke-width="2" style="width:14px;height:14px;"><path d="M12 15V3m0 0L7.5 7.5M12 3l4.5 4.5M5 13v6h14v-6"/></svg>
          <span style="color:#00E599;font-weight:800;letter-spacing:0.04em;">IMPOR PRESET</span>
        </button>
        <button id="homeLanguageBtn" class="rightBtn languageBtn" type="button" title="Bahasa" aria-label="Bahasa">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" aria-hidden="true" style="width:13px;height:13px;"><circle cx="12" cy="12" r="9"/><path d="M3.5 12h17M12 3c2.2 2.5 3.3 5.5 3.3 9S14.2 18.5 12 21M12 3C9.8 5.5 8.7 8.5 8.7 12S9.8 18.5 12 21"/></svg>
          <span id="homeLanguageCode" class="langCode">ID</span>
        </button>
        <!-- Hidden compat button for import file -->
        <button id="homeImportMain" class="hidden" type="button"></button>
        <button id="homeInstallBtn" class="hidden" type="button"></button>
      </div>
    </header>"""
    html, n_top = re.subn(old_top_actions_pattern, new_top_actions, html, count=1)
    print(f"Replaced homeTopActions: {n_top}")

    # 3. Redesign AMIndependentLinkUI into a sleek, simple, beautiful modal WITHOUT resolver choice!
    old_dialog_pattern = r'const AMIndependentLinkUI=\{[\s\S]*?open\(\)\{[\s\S]*?document\.body\.append\(dialog\);dialog\.showModal\(\);\s*\}\s*\};'
    new_dialog = """const AMIndependentLinkUI = {
  open() {
    const dialog = document.createElement('dialog');
    dialog.className = 'amDialog amImportDialog motionImportModal';
    dialog.innerHTML = `
      <div class="motionModalCard">
        <div class="motionModalHead">
          <div class="motionModalTitle">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#00E599" stroke-width="2.2"><path d="M12 15V3m0 0L7.5 7.5M12 3l4.5 4.5M5 13v6h14v-6"/></svg>
            <span>Impor Preset Motion</span>
          </div>
          <button data-close class="motionModalClose" type="button" aria-label="Tutup">×</button>
        </div>
        <p class="motionModalSub">Tempel link Alight Motion atau pilih file XML untuk langsung dimuat ke timeline.</p>
        
        <div class="motionInputBlock">
          <label class="motionInputLabel">Tautan Preset AM</label>
          <div class="motionInputRow">
            <input data-share type="url" autocomplete="off" spellcheck="false" placeholder="https://alightcreative.com/am/share/..." />
            <button data-paste type="button" class="motionBtn motionBtnPaste">Tempel</button>
          </div>
        </div>

        <div class="motionOrDivider"><span>atau</span></div>

        <button data-file-pick type="button" class="motionBtn motionBtnFile">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h7l2 2h7v14H4z"/></svg>
          <span>Pilih File XML / ZIP Proyek</span>
        </button>

        <p data-status class="motionModalStatus" role="status"></p>

        <div class="motionModalActions">
          <button data-import class="motionBtn motionBtnPrimary" type="button">⚡ Impor ke Timeline</button>
        </div>
      </div>
    `;

    const q = s => dialog.querySelector(s);
    const status = q('[data-status]');
    let busy = false;

    const close = () => { dialog.close(); dialog.remove(); };
    const setBusy = value => {
      busy = value;
      for (const e of dialog.querySelectorAll('button, input')) e.disabled = value;
    };

    q('[data-close]').onclick = close;

    q('[data-paste]').onclick = async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text && text.includes('http')) {
          q('[data-share]').value = text.trim();
          status.textContent = 'Tautan berhasil ditempel.';
        } else {
          status.textContent = 'Clipboard tidak berisi URL.';
        }
      } catch (err) {
        status.textContent = 'Silakan tempel (paste) manual di kolom input.';
      }
    };

    q('[data-file-pick]').onclick = () => {
      const fileInput = document.querySelector('#projectInput');
      if (fileInput) fileInput.click();
      close();
    };

    q('[data-import]').onclick = async () => {
      const link = q('[data-share]').value.trim();
      if (!link) {
        status.textContent = 'Silakan masukkan tautan preset terlebih dahulu.';
        return;
      }
      setBusy(true);
      status.textContent = 'Memeriksa tautan preset…';
      try {
        let report = null;
        try {
          report = await AMLinkPackageImporter.import(link, '', 'official', msg => {
            status.textContent = amImportDisplayText(msg);
          });
        } catch (officialErr) {
          console.warn('[Official resolver error, mencoba resolver cadangan]:', officialErr);
          status.textContent = 'Mengunduh melalui resolver cadangan…';
          report = await AMLinkPackageImporter.import(link, '', 'zervida', msg => {
            status.textContent = amImportDisplayText(msg);
          });
        }
        if (report) {
          if (typeof toast === 'function') toast('Preset berhasil diimpor ke timeline!');
          close();
        } else {
          status.textContent = 'Impor dibatalkan.';
        }
      } catch (err) {
        console.error('[Import Error]:', err);
        status.textContent = 'Gagal mengimpor: ' + (err.message || 'Periksa tautan');
      } finally {
        setBusy(false);
      }
    };

    dialog.oncancel = event => { if (busy) event.preventDefault(); };
    dialog.addEventListener('close', () => dialog.remove(), { once: true });
    document.body.append(dialog);
    dialog.showModal();
  }
};"""

    html, n_dlg = re.subn(old_dialog_pattern, new_dialog, html, count=1)
    print(f"Replaced AMIndependentLinkUI: {n_dlg}")

    # 4. FIX AM Effects bug: Ensure adjustment layers and effect layers are NEVER hidden in XMLBridge.parse
    old_adj_pattern = r"const adjustment=effectNodes\.some\(n=>/\\\.displacemap3\$\/\.test\(A\(n,'id'\)\)\|\|\(/\\\.lift\$\/\.test\(A\(n,'id'\)\)&&\[\.\.\.n\.children\]\.some\(p=>A\(p,'name'\)==='fill'&&N\(p,'value',1\)===0\)\)\);\s*if\(adjustment&&type==='shape'\)\{\s*l\.amImport\.originalHidden=l\.hidden;l\.hidden=true;l\.amImport\.previewDisabled=true;\s*project\.amWarnings\.push\(`\$\{l\.name\}: layer penyesuaian disimpan, preview dinonaktifkan karena efek AM belum didukung\.\`\);\s*\}"
    new_adj = """const adjustment=effectNodes.some(n=>/\\.displacemap3$/.test(A(n,'id'))||(/\\.lift$/.test(A(n,'id'))&&[...n.children].some(p=>A(p,'name')==='fill'&&N(p,'value',1)===0)));
        // Layer penyesuaian dan efek tetap ditampilkan dan dirender
        if(adjustment&&type==='shape'){
          l.hidden = A(el, 'hidden') === 'true';
          l.amImport.previewDisabled = false;
        }"""
    html, n_adj = re.subn(old_adj_pattern, new_adj, html, count=1)
    print(f"Fixed XMLBridge adjustment layer hiding: {n_adj}")

    # 5. FIX AM shader renderFrame crash: Catch error and safely fall back so layers ALWAYS render!
    old_render_catch = r"\}catch\(error\)\{console\.error\('AM shader render failed',error\);this\.stats\.error=error\.message;throw error\}"
    new_render_catch = """}catch(error){
      console.warn('AM shader render fallback:', error);
      this.stats.error = error.message;
      r.amFramePresented = false;
      return false; // Fallback to standard renderer so layers ALWAYS render!
    }"""
    html, n_rc = re.subn(old_render_catch, new_render_catch, html, count=1)
    print(f"Fixed AM shader renderFrame crash: {n_rc}")

    # 6. FIX individual effect passes inside AMEffectGPU.apply so bad effect uniforms don't drop layers
    old_apply_loop = r"for\(const fx of fxs\)\{if\(fx\.disabled\)continue;const program=e\.programs\.get\(fx\.id\);if\(!program\?\.programsByGroup\)continue;"
    new_apply_loop = """for(const fx of fxs){
      if(fx.disabled)continue;
      try{
        const program=e.programs.get(fx.id);if(!program?.programsByGroup)continue;"""
    
    old_apply_end = r"gl\.drawArrays\(gl\.TRIANGLES,0,6\);texture=dest\.tex;s\.passes\+\+\}\s*\}\s*\}return texture;"
    new_apply_end = """gl.drawArrays(gl.TRIANGLES,0,6);texture=dest.tex;s.passes++}
        }
      }catch(fxPassErr){
        console.warn('Skipping failing effect pass: '+fx.id, fxPassErr);
      }
    }return texture;"""
    html = html.replace(old_apply_loop, new_apply_loop)
    html = html.replace(old_apply_end, new_apply_end)
    print("Wrapped AMEffectGPU.apply in resilient try-catch")

    # 7. Add Alight Motion Mobile UI Styling (mobile-first, neat timeline, sleek dark palette, emerald green accents)
    am_ui_css = """
/* =========================================================
   Alight Motion Signature UI & Mobile-First Styling
   ========================================================= */
:root {
  --am-bg: #0f121a;
  --am-surface: #161b26;
  --am-surface-2: #1e2433;
  --am-line: rgba(255, 255, 255, 0.08);
  --am-accent: #00E599;
  --am-accent-glow: rgba(0, 229, 153, 0.28);
  --am-accent-dim: rgba(0, 229, 153, 0.12);
  --am-text: #f8fafc;
  --am-muted: #8e9bb0;
  --am-video: #22d3ee;
  --am-shape: #00E599;
  --am-text-layer: #f59e0b;
  --am-audio: #a855f7;
  --am-camera: #3b82f6;
}

/* Mobile-first Studio Container */
@media (max-width: 600px) {
  body {
    background: var(--am-bg) !important;
  }
  .app {
    width: 100vw !important;
    height: 100vh !important;
    height: 100dvh !important;
  }
  .homeMain {
    width: 100% !important;
    padding: 16px 12px 88px !important;
  }
  .editorMain {
    grid-template-rows: minmax(200px, 48%) minmax(210px, 52%) !important;
  }
}

/* Alight Motion Navigation and Brand */
.simpleHome .homeTop {
  height: 60px !important;
  padding: 0 16px !important;
  background: rgba(15, 18, 26, 0.94) !important;
  border-bottom: 1px solid var(--am-line) !important;
}
.simpleHome .homeWordmark b {
  color: var(--am-text) !important;
  font-size: 16px !important;
  font-weight: 850 !important;
  letter-spacing: -0.02em !important;
}
.simpleHome .motionImportBtn {
  background: var(--am-accent-dim) !important;
  border: 1px solid rgba(0, 229, 153, 0.35) !important;
  color: var(--am-accent) !important;
  border-radius: 999px !important;
  padding: 0 13px !important;
  height: 34px !important;
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
.simpleHome .motionImportBtn:hover,
.simpleHome .motionImportBtn:active {
  background: rgba(0, 229, 153, 0.22) !important;
  border-color: var(--am-accent) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 14px var(--am-accent-glow) !important;
}
.simpleHome .languageBtn {
  border-radius: 999px !important;
  height: 34px !important;
  padding: 0 10px !important;
}

/* Alight Motion Floating Action Button */
.simpleHome .fabHome, .fabHome {
  background: var(--am-accent) !important;
  color: #061a12 !important;
  font-size: 26px !important;
  border-radius: 50% !important;
  width: 56px !important;
  height: 56px !important;
  box-shadow: 0 8px 24px var(--am-accent-glow) !important;
  border: 4px solid var(--am-bg) !important;
  transition: transform 0.14s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.14s !important;
}
.simpleHome .fabHome:hover {
  transform: translateY(-2px) scale(1.04) !important;
  box-shadow: 0 12px 30px var(--am-accent-glow) !important;
}

/* Tampilan Timeline Rapi & Elegan */
.timelineArea {
  background: #121622 !important;
  border-top: 1px solid var(--am-line) !important;
}
.transport {
  background: #141824 !important;
  border-bottom: 1px solid var(--am-line) !important;
  height: 42px !important;
  padding: 0 10px !important;
}
.transport button {
  width: 36px !important;
  height: 34px !important;
  border-radius: 8px !important;
  color: #a4b1c7 !important;
}
.transport button.active,
.transport button:active {
  color: var(--am-accent) !important;
  background: var(--am-accent-dim) !important;
}
.timeRead {
  background: #090c13 !important;
  border: 1px solid #202738 !important;
  border-radius: 8px !important;
  color: #e2e8f0 !important;
  font-size: 10px !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  padding: 5px 9px !important;
}
.trackHead {
  background: #161b28 !important;
  border-right: 1px solid var(--am-line) !important;
  border-bottom: 1px solid var(--am-line) !important;
}
.trackHead.sel {
  background: #1f2638 !important;
}
.trackLane {
  border-bottom: 1px solid var(--am-line) !important;
}
.clip {
  border-radius: 5px !important;
  font-weight: 800 !important;
  letter-spacing: 0.02em !important;
  box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
}
.clip.shape { background: #00E599 !important; color: #041f15 !important; }
.clip.text { background: #f59e0b !important; color: #1c1002 !important; }
.clip.image { background: #06b6d4 !important; color: #021a1f !important; }
.clip.video { background: #0ea5e9 !important; color: #021524 !important; }
.clip.audio { background: #a855f7 !important; color: #190526 !important; }
.clip.sel {
  outline: 2px solid #ffffff !important;
  outline-offset: 1px !important;
  filter: brightness(1.08) !important;
}
.kf {
  background: #ff4d88 !important;
  border: 1.5px solid #ffffff !important;
  box-shadow: 0 0 6px rgba(255, 77, 136, 0.8) !important;
}
.playhead {
  background: var(--am-accent) !important;
  box-shadow: 0 0 8px var(--am-accent-glow) !important;
}
.playhead:before {
  background: var(--am-accent) !important;
}
.ruler {
  background: #0d1017 !important;
  border-bottom: 1px solid var(--am-line) !important;
}
.rTick {
  color: #64748b !important;
  border-left-color: rgba(255,255,255,0.08) !important;
}

/* Alight Motion Import Modal Styling */
.motionImportModal {
  border: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  max-width: min(460px, 92vw) !important;
  border-radius: 20px !important;
}
.motionModalCard {
  background: #141824 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 20px !important;
  padding: 20px !important;
  color: #f8fafc !important;
  box-shadow: 0 24px 64px rgba(0,0,0,0.65) !important;
}
.motionModalHead {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  margin-bottom: 8px !important;
}
.motionModalTitle {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  color: #f8fafc !important;
}
.motionModalClose {
  border: 0 !important;
  background: transparent !important;
  color: #94a3b8 !important;
  font-size: 24px !important;
  line-height: 1 !important;
  cursor: pointer !important;
  padding: 0 !important;
}
.motionModalClose:hover { color: #f8fafc !important; }
.motionModalSub {
  font-size: 11px !important;
  color: #8e9bb0 !important;
  line-height: 1.45 !important;
  margin: 0 0 16px 0 !important;
}
.motionInputBlock {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
}
.motionInputLabel {
  font-size: 10px !important;
  font-weight: 700 !important;
  color: #cbd5e1 !important;
  letter-spacing: 0.02em !important;
}
.motionInputRow {
  display: grid !important;
  grid-template-columns: 1fr auto !important;
  gap: 8px !important;
}
.motionInputRow input {
  height: 42px !important;
  background: #0d111a !important;
  border: 1px solid #232b3d !important;
  border-radius: 10px !important;
  color: #f8fafc !important;
  padding: 0 12px !important;
  font-size: 11px !important;
}
.motionInputRow input:focus {
  border-color: var(--am-accent) !important;
  box-shadow: 0 0 0 1px var(--am-accent) !important;
}
.motionBtn {
  border: 0 !important;
  border-radius: 10px !important;
  cursor: pointer !important;
  font-weight: 750 !important;
  font-size: 11px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 6px !important;
  transition: all 0.14s ease !important;
}
.motionBtnPaste {
  background: #1e2536 !important;
  border: 1px solid #303b54 !important;
  color: #e2e8f0 !important;
  padding: 0 14px !important;
  height: 42px !important;
}
.motionBtnPaste:active { background: #28334a !important; }
.motionOrDivider {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  margin: 14px 0 !important;
  position: relative !important;
}
.motionOrDivider:before {
  content: "" !important;
  position: absolute !important;
  left: 0; right: 0; height: 1px;
  background: #232a3d !important;
}
.motionOrDivider span {
  position: relative !important;
  background: #141824 !important;
  padding: 0 10px !important;
  color: #64748b !important;
  font-size: 10px !important;
  text-transform: uppercase !important;
}
.motionBtnFile {
  width: 100% !important;
  height: 42px !important;
  background: #171d2b !important;
  border: 1px dashed #334155 !important;
  color: #cbd5e1 !important;
  margin-bottom: 12px !important;
}
.motionBtnFile:hover { border-color: var(--am-accent) !important; color: var(--am-accent) !important; }
.motionModalStatus {
  min-height: 18px !important;
  font-size: 11px !important;
  color: #00E599 !important;
  margin: 4px 0 14px 0 !important;
  text-align: center !important;
  font-weight: 600 !important;
}
.motionBtnPrimary {
  width: 100% !important;
  height: 46px !important;
  background: var(--am-accent) !important;
  color: #051c14 !important;
  font-size: 13px !important;
  font-weight: 850 !important;
  box-shadow: 0 8px 20px var(--am-accent-glow) !important;
}
.motionBtnPrimary:active { transform: scale(0.98) !important; filter: brightness(0.95) !important; }
.motionBtnPrimary:disabled { opacity: 0.5 !important; pointer-events: none !important; }
"""

    # Inject CSS before </style>
    style_end = html.find('</style>')
    if style_end != -1:
        html = html[:style_end] + "\n" + am_ui_css + "\n" + html[style_end:]
        print("Injected Alight Motion signature styles")

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"New length: {len(html)}")

if __name__ == '__main__':
    main()
