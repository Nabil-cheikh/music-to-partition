<template>
  <div class="pdf-thumbnail">
    <pdf v-if="pdfSrc" :src="pdfSrc" :page="page" />
  </div>
</template>

<script>
import pdf from 'pdfvuer';

export default {
  name: 'PdfThumbnail',
  components: {
    pdf
  },
  props: {
    pdfSrc: {
      type: String,
      required: true
    },
    page: {
      type: Number,
      default: 1
    }
  }
}
</script>

<style scoped>
.pdf-thumbnail {
  width: 200px;
  height: 280px; /* Ratio à ajuster selon ton PDF */
  overflow: hidden;
}
/* On désactive l'interactivité pour l'aperçu */
.pdf-thumbnail pdf {
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
