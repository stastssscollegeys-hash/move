import app from './app';

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`YouTube Research Tool running at http://localhost:${PORT}/youtube-research`);
});
