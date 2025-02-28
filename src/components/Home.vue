<template>
  <div class="home">
    <h1>Welcome to Music To Partition</h1>
    <!-- Upload section -->
    <div class="upload-section">
      <label for="fileUpload">Upload the music you want to convert into a partition here :</label>
      <input type="file" id="fileUpload" accept=".wav" @change="handleFileUpload"/>
    </div>

    <!-- Analysis -->
    <button @click="onAnalyse" :disabled="!selectedFile">
      Launch Partition generation
    </button>

    <!-- Analysis indicator -->
     <div v-if="analysisInProgress" class="analysis-status">
      <p>Generation incoming...</p>
     </div>

     <!-- List of generated partitions -->
      <div v-if="partitions.length > 0" class='partitions-list'>
        <h2>Generated partitions</h2>
        <ul>
          <li v-for="(partition, index) in partitions" :key="index"
              class="partition-item">
            <!-- <PdfThumbnail :pdfSrc="partition.pdfSrc" :page="1"></PdfThumbnail> -->
            <div>
              <a
                :href="partition.pdfSrc"
                target="_blank"
                download>
                Partition {{ index + 1 }} ({{ partition.instrument }})
              </a>
            </div>
          </li>
        </ul>
      </div>
  </div>
</template>

<script>
// import PdfThumbnail from './PdfThumbnail.vue';

export default {
  name: 'Home',
  // components: {PdfThumbnail},
  data() {
    return {
      selectedFile: null,
      analysisInProgress: false,
      partitions: []
    }
  },
  methods: {
    handleFileUpload(event) {
      const file = event.target.files[0];
      console.log(event)
      if (file && file.type == 'audio/x-wav') {
        this.selectedFile = file;
      } else {
        alert('Veuillez sélectionner un fichier au format WAV.');
        event.target.value = null;
        this.selectedFile = null;
      }
    },

    onAnalyse() {
      this.analysisInProgress = true;

      // Simulated generation
      setTimeout(() => {
        // Here it should give partition files to download
        this.partitions = [
          {
            instrument: 'Piano',
            pdfSrc: '/data/HymnealaJoiePartition.pdf'
          },
          {
            instrument: 'Violin',
            pdfSrc: '/data/ViolinConcertoPartition.pdf'
          }
        ]
        this.analysisInProgress = false;
      }, 2000);
    }
  }
}
</script>

<style scoped>
.home {
  text-align: center;
  margin-top: 50px;
}

.upload-section {
  margin-bottom: 20px;
}

.analysis-status {
  margin: 20px 0;
  font-style: italic;
}

.partitions-list {
  margin-top: 30px;
}

.partition-item {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
}

</style>
