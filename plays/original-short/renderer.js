(function (root) {
  'use strict';
  class Renderer {
    constructor(canvas, manifest, images, story) {
      const { width: W, height: H } = story.stage;
      this.width = W; this.height = H;
      this.theme = story.presentation?.theme || {};
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      if (!this.ctx) throw new Error('Браузер не поддерживает Canvas 2D.');
      this.manifest = manifest;
      this.images = images;
      this.storyFaces = story.faces || {};
      this.curtain = document.createElement('canvas');
      this.curtain.width = W / 2; this.curtain.height = H;
      const ctx = this.curtain.getContext('2d');
      for (let x = 0; x < W / 2; x++) {
        const fold = Math.pow(.5 + .5 * Math.cos(x / 31), .6);
        const base = this.theme.curtain || '#6e2433';
        const rgb = [1,3,5].map(i => parseInt(base.slice(i, i + 2), 16) * (.7 + .3 * fold));
        ctx.fillStyle = `rgb(${rgb.join(',')})`;
        ctx.fillRect(x, 0, 1, H);
      }
      ctx.fillStyle = this.theme.gold || '#bf9652'; ctx.fillRect(0, H - 10, W / 2, 3);
      this.scale = 1;
    }
    resize(width) {
      const W = this.width, H = this.height;
      const ratio = Math.min(root.devicePixelRatio || 1, 2);
      const scale = width / W * ratio;
      this.canvas.width = Math.max(1, Math.round(W * scale));
      this.canvas.height = Math.max(1, Math.round(H * scale));
      this.scale = this.canvas.width / W;
    }
    drawCutout(record) {
      const { item, state, x, y } = record;
      if (!state.visible) return null;
      const asset = this.manifest.assets[state.asset], image = this.images[state.asset];
      const [left, top, right, bottom] = asset.bounds;
      const height = item.height * state.scale, width = height * (right - left) / (bottom - top) * state.width_scale;
      const ax = asset.anchor[0], ay = asset.anchor[1];
      const angle = (state.angle + record.angle) * -Math.PI / 180;
      const ctx = this.ctx;
      ctx.save(); ctx.translate(x, y); ctx.rotate(angle); ctx.scale(state.flip ? -1 : 1, 1);
      ctx.drawImage(image, left, top, right - left, bottom - top, -ax * width, -ay * height, width, height);
      ctx.restore();
      const head = asset.head_anchor || [.5, .1];
      const hx = (head[0] - ax) * width * (state.flip ? -1 : 1), hy = (head[1] - ay) * height;
      return { x: x + hx * Math.cos(angle) - hy * Math.sin(angle),
               y: y + hx * Math.sin(angle) + hy * Math.cos(angle) };
    }
    faceImage(slug, emotion) {
      return this.images[`faces:${slug}:${emotion}`]
        || this.images[`faces:${slug}:neutral`]
        || this.images[`faces:${slug}:${Object.keys(this.storyFaces[slug] || {})[0]}`];
    }
    drawPortrait(slug, emotion, cx, cy, size, dim) {
      const image = this.faceImage(slug, emotion);
      if (!image) return null;
      const ctx = this.ctx;
      ctx.save();
      ctx.globalAlpha = dim ? .55 : 1;
      // Soft oval vignette instead of a rectangular portrait card.
      ctx.beginPath();
      ctx.ellipse(cx, cy, size * .5, size * .58, 0, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(image, cx - size / 2, cy - size * .58, size, size * 1.16);
      ctx.restore();
      ctx.save();
      ctx.globalAlpha = dim ? .5 : .95;
      ctx.strokeStyle = this.theme.gold || '#bf9652';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(cx, cy, size * .5, size * .58, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
      return { x: cx, y: cy - size * .3 };
    }
    drawCloseup(frame) {
      const block = frame.closeup;
      if (!block?.cast?.length || frame.curtain < .9 || frame.ended) return null;
      const cast = block.cast;
      const W = this.width, H = this.height, ctx = this.ctx;
      // Paper wash: the room stays readable but recedes behind the faces.
      ctx.save();
      ctx.fillStyle = 'rgba(244, 234, 214, .74)';
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
      const size = cast.length > 1 ? H * .60 : H * .64;
      const gap = size * .16;
      const total = cast.length * size + (cast.length - 1) * gap;
      let left = (W - total) / 2;
      const speaker = block.speaker;
      const anchors = new Map();
      cast.forEach((slug, index) => {
        const actor = frame.actors.get(slug);
        const emotion = (actor?.state.asset || `${slug}-neutral`).split('-').pop();
        const dim = slug !== speaker;
        const cx = left + size / 2 + index * (size + gap);
        const cy = H * .34;
        const anchor = this.drawPortrait(slug, emotion, cx, cy, dim ? size * .92 : size, dim);
        if (anchor && actor) anchors.set(slug, anchor);
      });
      return anchors;
    }
    draw(frame) {
      const W = this.width, H = this.height;
      const ctx = this.ctx;
      ctx.setTransform(this.canvas.width / W, 0, 0, this.canvas.height / H, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const bg = this.images[frame.scene.background];
      const scale = Math.max(W / bg.naturalWidth, H / bg.naturalHeight);
      const sw = W / scale, sh = H / scale;
      ctx.drawImage(bg, (bg.naturalWidth - sw) / 2, bg.naturalHeight - sh, sw, sh, 0, 0, W, H);
      const heads = new Map();
      const closeupMode = Boolean(frame.closeup && frame.curtain >= .9 && !frame.ended);
      if (!closeupMode) {
        for (const item of frame.items) {
          const head = this.drawCutout(item);
          if (head && frame.actors.has(item.item.id)) heads.set(item.item.id, head);
        }
      }
      const closeup = this.drawCloseup(frame);
      if (closeup) for (const [slug, anchor] of closeup) heads.set(slug, anchor);
      const travel = W / 2 * frame.curtain;
      ctx.drawImage(this.curtain, -travel, 0, W / 2, H);
      ctx.save(); ctx.translate(W + travel, 0); ctx.scale(-1, 1); ctx.drawImage(this.curtain, 0, 0, W / 2, H); ctx.restore();
      ctx.fillStyle = this.theme.curtain || '#591823'; ctx.fillRect(0, 0, W, 12);
      ctx.fillStyle = this.theme.gold || '#bf9652'; ctx.fillRect(0, 12, W, 2);
      const result = { heads };
      if (closeup) result.closeup = true;
      return result;
    }
  }
  root.SpriteRenderer = Renderer;
})(globalThis);
