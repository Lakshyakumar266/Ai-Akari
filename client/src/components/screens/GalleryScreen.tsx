import React from "react";
import "./GalleryScreen.css";

interface GalleryScreenProps {
  character: string;
}

export const GalleryScreen: React.FC<GalleryScreenProps> = ({ character }) => {
  const displayName = character.charAt(0).toUpperCase() + character.slice(1);

  return (
    <div className="gallery-screen-root" aria-label="Character Gallery Screen">
      {/* Floating Model Meta Card */}
      <div className="gallery-info-card">
        <h2 className="gallery-title">{displayName} Model Showcase</h2>
        <div className="gallery-meta-list">
          <div className="gallery-meta-item">
            <span className="gallery-meta-label">Format</span>
            <span>VRM 1.0</span>
          </div>
          <div className="gallery-meta-item">
            <span className="gallery-meta-label">Outfit</span>
            <span>Default Casual</span>
          </div>
          <div className="gallery-meta-item">
            <span className="gallery-meta-label">Expressions</span>
            <span>Morph Target Sync</span>
          </div>
        </div>
      </div>
    </div>
  );
};
