// frontend/pages/index.js
import Head from 'next/head';
import styles from '../styles/Home.module.css'; // We'll create this file next

export default function Home() {
  // TODO: Replace with actual GitHub App installation URL
  const GITHUB_APP_INSTALL_URL = "https://github.com/apps/YOUR_APP_NAME/installations/new"; 

  return (
    <div className={styles.container}>
      <Head>
        <title>CodeGuardian AI - Automated Security Reviews</title>
        <meta name="description" content="Get AI-powered security reviews directly in your GitHub Pull Requests." />
        <link rel="icon" href="/favicon.ico" /> {/* Add a favicon later */}
      </Head>

      <main className={styles.main}>
        <h1 className={styles.title}>
          Welcome to <a href="#">CodeGuardian AI</a>
        </h1>

        <p className={styles.description}>
          Supercharge your code reviews with AI-driven security analysis.
          <br />
          Get instant feedback on potential vulnerabilities directly in your GitHub Pull Requests.
        </p>

        <div className={styles.ctaContainer}>
          <a href={GITHUB_APP_INSTALL_URL} className={styles.ctaButton} target="_blank" rel="noopener noreferrer">
            Install GitHub App
          </a>
          <p className={styles.subtleText}>Start securing your Python projects today!</p>
        </div>

        {/* Optional: Add more sections later (features, how it works, etc.) */}
      </main>

      <footer className={styles.footer}>
        <p>Powered by AI</p>
        {/* Add footer links if needed */}
      </footer>
    </div>
  );
}

