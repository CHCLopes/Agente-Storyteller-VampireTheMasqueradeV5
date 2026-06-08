import React from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
      id="modal-container"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div 
        className="w-full max-w-xl bg-v5-card dark:bg-v5-card light:bg-v5light-card border-2 border-v5-crimson dark:border-v5-crimson light:border-v5light-earth rounded shadow-2xl p-6 relative select-text"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Botão Fechar */}
        <button
          onClick={onClose}
          id="btn-close-modal"
          className="absolute top-4 right-4 p-1 rounded hover:bg-zinc-800 dark:hover:bg-zinc-800 light:hover:bg-v5light-border/40 transition-colors cursor-pointer"
          aria-label="Fechar modal"
        >
          <X className="w-5 h-5 text-primary" style={{ color: 'var(--text-primary)' }} />
        </button>

        {/* Título */}
        <h2 
          id="modal-title"
          className="font-serif text-xl font-bold border-b border-zinc-800 dark:border-zinc-800 light:border-v5light-border pb-2 pr-6 text-primary mb-4 text-left"
          style={{ color: 'var(--text-primary)' }}
        >
          {title}
        </h2>

        {/* Conteúdo */}
        <div 
          id="modal-body"
          className="text-sm space-y-4 text-left leading-relaxed text-secondary"
          style={{ color: 'var(--text-secondary)' }}
        >
          {children}
        </div>
      </div>
    </div>
  );
};

export const AboutModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Sobre o Motor Narrativo V5">
      <p>
        Este sistema é um motor de orquestração local de Inteligência Artificial desenhado sob rigorosas práticas da <strong>Mentoria Vibe Coding</strong>.
      </p>
      <p>
        O backend opera em <strong>FastAPI</strong> com suporte reativo a <strong>WebSockets</strong> nativos para streaming síncrono e assíncrono das crônicas.
      </p>
      <p>
        A persistência é garantida atonicamente sob <code>asyncio.Lock()</code> com I/O em arquivos do PlayerSheet.
      </p>
    </Modal>
  );
};

export const HelpModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Guia de Operação da Crônica">
      <p><strong>Comandos Principais:</strong></p>
      <ul className="list-dash pl-5 space-y-1.5 list-disc">
        <li>Digite <em>&quot;Inicie uma nova crônica.&quot;</em> para começar uma jornada das sombras.</li>
        <li>Digite as ações do seu Neófito livremente na caixa de diálogo central ou no <strong>Textarea de entrada</strong> de 4 linhas. Pressione <em>Enter</em> para enviar.</li>
        <li>Utilize os <strong>Dropdowns da Ficha</strong> para ativar disciplinas ou usar habilidades de forma instantânea com auto-submissão reativa.</li>
      </ul>
    </Modal>
  );
};
