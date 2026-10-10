"use client";

import { useState, useSyncExternalStore } from "react";
import { ADMIN_KEY, api } from "@/lib/api";
import { PinLabel } from "./ui";

function listen(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function hasCode() {
  try { return !!localStorage.getItem(ADMIN_KEY); } catch { return false; }
}

export function AdminCode() {
  const [code, setCode] = useState("");
  const saved = useSyncExternalStore(listen, hasCode, () => false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setError("");
    setBusy(true);
    try {
      await api.adminCheck(code);
      localStorage.setItem(ADMIN_KEY, code);
      window.dispatchEvent(new Event("storage"));
      setCode("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function forget() {
    try { localStorage.removeItem(ADMIN_KEY); } catch { /* ignore */ }
    window.dispatchEvent(new Event("storage"));
  }

  return (
    <div className="w-full max-w-sm">
      <h1 className="font-display text-[34px] leading-[0.95] font-black uppercase">Équipe Paginya</h1>
      {saved ? (
        <>
          <p className="mt-3 text-[16px] text-ink/75">
            Cet appareil est reconnu. Au moment de payer, choisis « Équipe Paginya : débloquer sans payer ».
          </p>
          <button type="button" onClick={forget} className="mt-5 text-[15px] font-semibold text-ink/60 underline">Oublier le code sur cet appareil</button>
        </>
      ) : (
        <>
          <p className="mt-3 text-[16px] text-ink/75">Entre le code de l&apos;équipe : tes documents seront gratuits sur cet appareil.</p>
          <input
            type="password"
            autoComplete="off"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Code"
            className="mt-4 w-full rounded-md bg-paper px-3.5 py-3.5 text-[19px] ring-1 ring-black/10 focus:outline-none"
          />
          {error && <p className="mt-2 text-[14px] text-pin">{error}</p>}
          <PinLabel className="mt-4 w-full" disabled={busy || !code} onClick={save}>{busy ? "Un instant…" : "Enregistrer"}</PinLabel>
        </>
      )}
    </div>
  );
}
