# -*- coding: utf-8 -*-
"""Chapter 8 (Conclusion), Chapter 9 (References) and the appendices.

Chapter 7 is generated (`content_research.py`) and is rendered between
content_b and this file. Because its length varies with the experiments, the
figure and table numbers used here are not fixed at import time: the builder
calls `set_label_offsets()` with the last number Chapter 7 used, and this
module rebuilds BLOCKS around it.
"""

# Fallback offsets, used only if the builder does not call set_label_offsets
# (i.e. a checkout that has not run `make research` yet, where Chapter 7 is
# absent). content_b ends at Figure 29 / Table 14.
_FIG0, _TAB0 = 29, 14


def _build(fig0, tab0):
    def T(n):
        return f"Table {tab0 + n}"

    return [
        # ============================================== CHAPTER 8
        ("h1", "CHAPTER 8 — CONCLUSION"),

        ("h2", "8.1 Conclusion"),
        ("p", "This project set out to determine whether the four principal "
              "functions of digital marketing — audience targeting, campaign "
              "automation, analytics and content production — can be operated "
              "as a single measurable feedback loop, and whether such a loop "
              "remains useful for a newly launched product that has almost no "
              "data. Both questions are answered affirmatively, with "
              "qualifications that the evidence in Chapter 7 makes explicit "
              "rather than leaves implied."),
        ("p", "A complete, running system was delivered: four research modules "
              "behind a FastAPI service over PostgreSQL, a Next.js dashboard, "
              "a demonstration e-commerce store carrying a first-party "
              "tracking snippet, and an 8,000-customer research audience "
              "imported through the same path a live visitor uses. The system "
              "is reproducible from a clean checkout, covered by 260 automated "
              "tests, and accompanied by eleven experiments that regenerate "
              "every table, figure and chapter of the evaluation with one "
              "command."),
        ("p", "The eleven objectives of Section 1.4.2 were met. What "
              "distinguishes the outcome is that meeting them produced several "
              "results the team did not expect and would not have chosen."),

        ("h2", "8.2 Principal Findings"),
        ("p", "Four findings are substantive contributions in their own "
              "right."),
        ("p", "**A hybrid method must be measured against its own "
              "components.** The segmentation engine separates conversion by "
              "0.3838; its own rules, alone, reach 0.3837. The clustering "
              "contributes nothing to that metric, and the finding is only "
              "available because the ablation was run. The hybrid keeps its "
              "place in the system on different and defensible grounds — it "
              "produces a calibrated confidence from three-way agreement, and "
              "the vote is what makes cold start explicit — but the claim "
              "that it separates conversion better than a handful of "
              "interpretable rules is not supported, and is not made."),
        ("p", "**Accuracy is not what a leak corrupts.** The confidence model "
              "trained with its own target among the inputs was 0.9213 "
              "accurate; corrected, it is 0.9200. The difference is 0.0013. "
              "But 450 customers emerged at confidence 1.00 with the leak "
              "against 3 without it — a 150-fold inflation of certainty. A "
              "model whose accuracy is honest while its confidence is not "
              "will be trusted in exactly the cases where it should not be, "
              "and no test will go red."),
        ("p", "**Attribution models do not merely differ; they disagree "
              "enough to reverse a spending decision.** Across 7,811 "
              "converting journeys the widest pair of models disagrees over "
              "68 % of all attributed credit, and 20 % of those journeys have "
              "a single touchpoint, where every model agrees by arithmetic "
              "rather than by evidence. A company reading only last-touch "
              "would conclude that email is responsible for almost everything "
              "and cut the acquisition spend that built the audience."),
        ("p", "**A recommender that ranks by predicted response is answering "
              "a different question from the one a campaign asks, and a "
              "system that does not log propensities cannot discover that for "
              "itself.** On randomised data the response-ranking and "
              "uplift-ranking policies share only 56 % of a 30 % budget. "
              "Establishing which is better for *this* system's actions "
              "requires this system's own data — so it now records every "
              "decision with the probability it was taken under, and explores "
              "on purpose. Validation against a known answer shows that "
              "without exploration the estimate is biased **upwards** while "
              "its standard diagnostic looks *better*, not worse. Stability is "
              "not correctness."),

        ("h2", "8.3 Methodological Contribution"),
        ("p", "The project's methodological contribution is of comparable "
              "weight to its technical one. Seven defects were found in the "
              "team's own research code. Every one inflated a result and none "
              "produced an error message. Their correction changed headline "
              "figures materially — an engagement R² of 0.99 became −0.168, a "
              "confidence column that read 1.00 for 450 customers read it for "
              "3, and a cold-start segment that had silently emptied to zero "
              "was restored."),
        ("p", "That experience shaped the system's design. Provenance is "
              "derived at write time rather than asserted by a caller. The "
              "importer preserves measured totals exactly and declares what it "
              "reconstructs. Propensity is a mandatory column, not an optional "
              "one. Refusal thresholds suppress output the data cannot "
              "support. Chapter 7 is generated from the results file, so a "
              "figure cannot drift from the number it plots. Each of these is "
              "a small engineering decision whose purpose is to make "
              "overstating a result structurally difficult rather than merely "
              "discouraged."),

        ("h2", "8.4 Limitations"),
        ("p", "The limitations are stated in full in Section 7.6 and are not "
              "minor. The study audience is a real dataset of per-customer "
              "totals whose event ordering is reconstructed, so any result "
              "resting on timing is a property of that reconstruction. The "
              "policy ranking is not stable across how response is modelled. "
              "The uplift result comes from a borrowed dataset whose actions "
              "are not this system's actions, and its intervals overlap. The "
              "capability-detection sample is a development set, not a "
              "held-out one, and its accuracy figure is therefore fitted. The "
              "engagement corpus contains no usable text signal at all. None "
              "of these is concealed, because a framework whose purpose is to "
              "help marketers trust their measurements cannot be evaluated by "
              "a standard lower than the one it advocates."),

        ("h2", "8.5 Future Work"),
        ("numbers", [
            "**Run the loop long enough to close it with real decisions.** "
            "The decision log, the propensity column and the exploration "
            "mechanism are built and validated against a known answer. What "
            "remains is to accumulate enough live decisions for the estimator "
            "to be applied to this system's own policy rather than to a "
            "simulated one — a matter of volume, not of design.",
            "**A held-out capability sample.** Section 7.3.10 reports a "
            "fitted accuracy on a development set and says so. A fresh sample "
            "of websites never inspected during development would convert a "
            "verdict into a generalisation claim.",
            "**Live-audience validation of the predictive models.** Their "
            "ranking transfers to the imported audience; their absolute "
            "probabilities do not. Re-fitting on measured journeys would make "
            "thresholds, and not only orderings, usable.",
            "**A content corpus with genuine engagement signal.** The "
            "negative engagement result is a property of the dataset, not of "
            "the model. Collecting post-level text paired with post-level "
            "engagement from the platform's own campaigns — which the "
            "tracking layer already supports — would allow the model to be "
            "retrained and its weight restored if it earns it.",
            "**Growing the labelled goal and tone corpora.** Both classifiers "
            "are limited by corpus size rather than by method, and one tone "
            "class has too few examples to be learned or evaluated at all. "
            "Active learning over the assets the platform already generates "
            "would expand the rare classes.",
            "**Adaptive policy selection.** With a propensity-logged record "
            "in place, a contextual-bandit layer could select the automation "
            "policy per segment online, using the exploration budget the "
            "system already spends and the operational-complexity measure as "
            "an explicit cost term.",
            "**Privacy and regulatory hardening.** The tracking layer is "
            "first-party and honours Do Not Track, but consent management, "
            "retention policy and subject-access support would be required "
            "for commercial deployment.",
        ]),
        ("p", "The framework as delivered is a research instrument that "
              "happens to run as a product. Its value lies less in any single "
              "model than in demonstrating that the four marketing functions "
              "can be operated as one loop, that the effect of doing so can "
              "be measured rather than asserted, and that a system can be "
              "built to make its own results harder to overstate."),

        # ============================================== CHAPTER 9
        ("h1", "CHAPTER 9 — REFERENCES"),
        ("p", "[1] D. A. Aaker and C. Moorman, *Strategic Market Management*, "
              "11th ed. Hoboken, NJ, USA: Wiley, 2017."),
        ("p", "[2] C. C. Aggarwal, *Data Mining: The Textbook*. Cham, "
              "Switzerland: Springer, 2015."),
        ("p", "[3] M. Alves Gomes and T. Meisen, “A review on customer "
              "segmentation methods for personalized customer targeting in "
              "e-commerce use cases,” *Information Systems and e-Business "
              "Management*, vol. 21, no. 3, pp. 527–570, 2023."),
        ("p", "[4] A. Banks and E. Porcello, *Learning React*, 2nd ed. "
              "Sebastopol, CA, USA: O’Reilly Media, 2020."),
        ("p", "[5] J. Bobadilla, F. Ortega, A. Hernando, and A. Gutiérrez, "
              "“Recommender systems survey,” *Knowledge-Based Systems*, "
              "vol. 46, pp. 109–132, 2013."),
        ("p", "[6] T. B. Brown et al., “Language models are few-shot "
              "learners,” *Advances in Neural Information Processing "
              "Systems*, vol. 33, pp. 1877–1901, 2020."),
        ("p", "[7] S. Chacon and B. Straub, *Pro Git*, 2nd ed. Berkeley, CA, "
              "USA: Apress, 2014."),
        ("p", "[8] D. Chaffey and F. Ellis-Chadwick, *Digital Marketing: "
              "Strategy, Implementation and Practice*, 8th ed. Harlow, UK: "
              "Pearson, 2022."),
        ("p", "[9] D. Chaffey, T. Hemphill, and D. Edmundson-Bird, *Digital "
              "Business and E-Commerce Management*, 8th ed. Harlow, UK: "
              "Pearson, 2024."),
        ("p", "[10] D. Court, D. Elzinga, S. Mulder, and O. J. Vetvik, “The "
              "consumer decision journey,” *McKinsey Quarterly*, vol. 3, "
              "pp. 96–107, 2009."),
        ("p", "[11] B. Dalessandro, C. Perlich, O. Stitelman, and F. Provost, "
              "“Causally motivated attribution for online advertising,” in "
              "*Proc. 6th Int. Workshop on Data Mining for Online Advertising "
              "and Internet Economy (ADKDD)*, 2012, pp. 1–9."),
        ("p", "[12] T. H. Davenport, A. Guha, D. Grewal, and T. Bressgott, "
              "“How artificial intelligence will change the future of "
              "marketing,” *Journal of the Academy of Marketing Science*, "
              "vol. 48, no. 1, pp. 24–42, 2020."),
        ("p", "[13] Y. K. Dwivedi et al., “Artificial Intelligence (AI): "
              "Multidisciplinary perspectives on emerging challenges, "
              "opportunities, and agenda for research, practice and policy,” "
              "*International Journal of Information Management*, vol. 57, "
              "Art. no. 101994, 2021."),
        ("p", "[14] A. Géron, *Hands-On Machine Learning with Scikit-Learn, "
              "Keras, and TensorFlow*, 3rd ed. Sebastopol, CA, USA: O’Reilly "
              "Media, 2022."),
        ("p", "[15] I. Goodfellow, Y. Bengio, and A. Courville, *Deep "
              "Learning*. Cambridge, MA, USA: MIT Press, 2016."),
        ("p", "[16] J. Han, J. Pei, and H. Tong, *Data Mining: Concepts and "
              "Techniques*, 4th ed. Cambridge, MA, USA: Morgan Kaufmann, "
              "2022."),
        ("p", "[17] T. Hastie, R. Tibshirani, and J. Friedman, *The Elements "
              "of Statistical Learning*, 2nd ed. New York, NY, USA: Springer, "
              "2009."),
        ("p", "[18] M. Haverbeke, *Eloquent JavaScript*, 4th ed. San "
              "Francisco, CA, USA: No Starch Press, 2024."),
        ("p", "[19] D. Herron, *Node.js Web Development*, 5th ed. Birmingham, "
              "UK: Packt Publishing, 2020."),
        ("p", "[20] S. Holm, “A simple sequentially rejective multiple test "
              "procedure,” *Scandinavian Journal of Statistics*, vol. 6, "
              "no. 2, pp. 65–70, 1979."),
        ("p", "[21] M.-H. Huang and R. T. Rust, “Artificial intelligence in "
              "service,” *Journal of Service Research*, vol. 21, no. 2, "
              "pp. 155–172, 2018."),
        ("p", "[22] J. Järvinen and H. Karjaluoto, “The use of Web analytics "
              "for digital marketing performance measurement,” *Industrial "
              "Marketing Management*, vol. 50, pp. 117–127, 2015."),
        ("p", "[23] B. Johnson, *Visual Studio Code: End-to-End Editing and "
              "Debugging Tools for Web Developers*. Hoboken, NJ, USA: Wiley, "
              "2019."),
        ("p", "[24] P. Kotler, H. Kartajaya, and I. Setiawan, *Marketing 5.0: "
              "Technology for Humanity*. Hoboken, NJ, USA: Wiley, 2021."),
        ("p", "[25] P. Kotler, K. L. Keller, and A. Chernev, *Marketing "
              "Management*, 16th ed. Harlow, UK: Pearson, 2021."),
        ("p", "[26] V. Kumar, A. Dixit, R. G. Javalgi, and M. Dass, “Digital "
              "transformation of marketing: A synthesis and research agenda,” "
              "*Journal of Business Research*, vol. 122, pp. 779–792, 2021."),
        ("p", "[27] V. Kumar and W. Reinartz, *Customer Relationship "
              "Management: Concept, Strategy, and Tools*, 3rd ed. Berlin, "
              "Germany: Springer, 2018."),
        ("p", "[28] J. Li, D. Li, C. Xiong, and S. C. H. Hoi, “BLIP: "
              "Bootstrapping language-image pre-training for unified "
              "vision-language understanding and generation,” in *Proc. Int. "
              "Conf. Machine Learning (ICML)*, 2022, pp. 12888–12900."),
        ("p", "[29] S. M. Lundberg and S.-I. Lee, “A unified approach to "
              "interpreting model predictions,” *Advances in Neural "
              "Information Processing Systems*, vol. 30, pp. 4765–4774, 2017."),
        ("p", "[30] Q. McNemar, “Note on the sampling error of the difference "
              "between correlated proportions or percentages,” "
              "*Psychometrika*, vol. 12, no. 2, pp. 153–157, 1947."),
        ("p", "[31] B. Marr and M. Ward, *Artificial Intelligence in "
              "Practice*. Hoboken, NJ, USA: Wiley, 2019."),
        ("p", "[32] W. McKinney, *Python for Data Analysis*, 3rd ed. "
              "Sebastopol, CA, USA: O’Reilly Media, 2022."),
        ("p", "[33] C. Molnar, *Interpretable Machine Learning*, 2nd ed., "
              "2022."),
        ("p", "[34] N. Cliff, “Dominance statistics: Ordinal analyses to "
              "answer ordinal questions,” *Psychological Bulletin*, vol. 114, "
              "no. 3, pp. 494–509, 1993."),
        ("p", "[35] R. O. Obe and L. S. Hsu, *PostgreSQL: Up and Running*, "
              "3rd ed. Sebastopol, CA, USA: O’Reilly Media, 2017."),
        ("p", "[36] F. Pedregosa et al., “Scikit-learn: Machine learning in "
              "Python,” *Journal of Machine Learning Research*, vol. 12, "
              "pp. 2825–2830, 2011."),
        ("p", "[37] F. Provost and T. Fawcett, *Data Science for Business*. "
              "Sebastopol, CA, USA: O’Reilly Media, 2013."),
        ("p", "[38] A. Radford et al., “Learning transferable visual models "
              "from natural language supervision,” in *Proc. Int. Conf. "
              "Machine Learning (ICML)*, 2021, pp. 8748–8763."),
        ("p", "[39] N. J. Radcliffe and P. D. Surry, “Real-world uplift "
              "modelling with significance-based uplift trees,” *Stochastic "
              "Solutions White Paper*, pp. 1–33, 2011."),
        ("p", "[40] F. Ricci, L. Rokach, and B. Shapira, Eds., *Recommender "
              "Systems Handbook*, 3rd ed. New York, NY, USA: Springer, 2022."),
        ("p", "[41] M. Riva, *Real-World Next.js*. Birmingham, UK: Packt "
              "Publishing, 2022."),
        ("p", "[42] A. I. Schein, A. Popescul, L. H. Ungar, and D. M. "
              "Pennock, “Methods and metrics for cold-start "
              "recommendations,” in *Proc. 25th Annu. Int. ACM SIGIR Conf. "
              "Research and Development in Information Retrieval*, 2002, "
              "pp. 253–260."),
        ("p", "[43] X. Shao and L. Li, “Data-driven multi-touch attribution "
              "models,” in *Proc. 17th ACM SIGKDD Int. Conf. Knowledge "
              "Discovery and Data Mining*, 2011, pp. 258–264."),
        ("p", "[44] R. S. Sutton and A. G. Barto, *Reinforcement Learning: An "
              "Introduction*, 2nd ed. Cambridge, MA, USA: MIT Press, 2018."),
        ("p", "[45] L. Tunstall, L. von Werra, and T. Wolf, *Natural Language "
              "Processing with Transformers*. Sebastopol, CA, USA: O’Reilly "
              "Media, 2022."),
        ("p", "[46] J. VanderPlas, *Python Data Science Handbook*, 2nd ed. "
              "Sebastopol, CA, USA: O’Reilly Media, 2022."),
        ("p", "[47] A. Vaswani et al., “Attention is all you need,” *Advances "
              "in Neural Information Processing Systems*, vol. 30, "
              "pp. 5998–6008, 2017."),
        ("p", "[48] S. Verma, R. Sharma, S. Deb, and D. Maitra, “Artificial "
              "intelligence in marketing: Systematic review and future "
              "research direction,” *International Journal of Information "
              "Management Data Insights*, vol. 1, no. 1, Art. no. 100002, "
              "2021."),
        ("p", "[49] M. Wedel and P. K. Kannan, “Marketing analytics for "
              "data-rich environments,” *Journal of Marketing*, vol. 80, "
              "no. 6, pp. 97–121, 2016."),
        ("p", "[50] T. Zhang, V. Kishore, F. Wu, K. Q. Weinberger, and "
              "Y. Artzi, “BERTScore: Evaluating text generation with BERT,” "
              "in *Proc. Int. Conf. Learning Representations (ICLR)*, 2020."),
        ("p", "[51] P. Gutierrez and J.-Y. Gérardy, “Causal inference and "
              "uplift modelling: A review of the literature,” in *Proc. 3rd "
              "Int. Conf. Predictive Applications and APIs (PMLR 67)*, 2017, "
              "pp. 1–13."),
        ("p", "[52] B. Efron and R. J. Tibshirani, *An Introduction to the "
              "Bootstrap*. New York, NY, USA: Chapman & Hall, 1993."),
        ("p", "[53] N. Reimers and I. Gurevych, “Sentence-BERT: Sentence "
              "embeddings using Siamese BERT-networks,” in *Proc. Conf. "
              "Empirical Methods in Natural Language Processing "
              "(EMNLP-IJCNLP)*, 2019, pp. 3982–3992."),
        ("p", "[54] S. Ramírez, “FastAPI documentation,” 2025. [Online]. "
              "Available: https://fastapi.tiangolo.com"),
        ("p", "[55] Vercel Inc., “Next.js documentation,” 2025. [Online]. "
              "Available: https://nextjs.org/docs"),
        ("p", "[56] The PostgreSQL Global Development Group, “PostgreSQL 16 "
              "documentation,” 2024. [Online]. Available: "
              "https://www.postgresql.org/docs/16/"),
        ("p", "[57] T. Chen and C. Guestrin, “XGBoost: A scalable tree "
              "boosting system,” in *Proc. 22nd ACM SIGKDD Int. Conf. "
              "Knowledge Discovery and Data Mining*, 2016, pp. 785–794."),
        ("p", "[58] K. Hillstrom, “The MineThatData e-mail analytics and data "
              "mining challenge,” MineThatData Blog, 2008. [Online]. "
              "Available: https://blog.minethatdata.com"),
        ("p", "[59] D. G. Horvitz and D. J. Thompson, “A generalization of "
              "sampling without replacement from a finite universe,” "
              "*Journal of the American Statistical Association*, vol. 47, "
              "no. 260, pp. 663–685, 1952."),
        ("p", "[60] M. Dudík, J. Langford, and L. Li, “Doubly robust policy "
              "evaluation and learning,” in *Proc. 28th Int. Conf. Machine "
              "Learning (ICML)*, 2011, pp. 1097–1104."),
        ("p", "[61] A. Swaminathan and T. Joachims, “The self-normalized "
              "estimator for counterfactual learning,” *Advances in Neural "
              "Information Processing Systems*, vol. 28, pp. 3231–3239, "
              "2015."),
        ("p", "[62] L. Li, W. Chu, J. Langford, and X. Wang, “Unbiased "
              "offline evaluation of contextual-bandit-based news article "
              "recommendation algorithms,” in *Proc. 4th ACM Int. Conf. Web "
              "Search and Data Mining (WSDM)*, 2011, pp. 297–306."),
        ("p", "[63] P. J. Rousseeuw, “Silhouettes: A graphical aid to the "
              "interpretation and validation of cluster analysis,” *Journal "
              "of Computational and Applied Mathematics*, vol. 20, pp. 53–65, "
              "1987."),
        ("p", "[64] E. B. Wilson, “Probable inference, the law of succession, "
              "and statistical inference,” *Journal of the American "
              "Statistical Association*, vol. 22, no. 158, pp. 209–212, 1927."),
        ("p", "[65] F. Wilcoxon, “Individual comparisons by ranking methods,” "
              "*Biometrics Bulletin*, vol. 1, no. 6, pp. 80–83, 1945."),

        # ============================================== APPENDIX A
        ("h1", "APPENDIX A — INDIVIDUAL CONTRIBUTION"),
        ("p", "The project was divided into four research modules, one per "
              "team member, with the integration layer, the experimental "
              "apparatus and the report shared. Each member owned the design, "
              "implementation, evaluation and documentation of their module, "
              "and contributed to the integrated platform."),

        ("h2", "A.1  215001G — Aadhil M. H. M."),
        ("h3", "Module 4 — AI Content Refinery and Multi-Platform "
               "Distribution"),
        ("p", "I was responsible for the design, implementation and evaluation "
              "of the AI content refinery. I built the crawler that extracts a "
              "site's page copy, headings and product descriptions, and the "
              "knowledge-base component that condenses them into the business "
              "summary and brand vocabulary used to ground every generated "
              "asset. During this work I diagnosed and fixed a "
              "character-encoding fault in which the HTTP library defaulted to "
              "ISO-8859-1 for `text/html` responses whose headers omitted a "
              "charset, corrupting every non-ASCII character in a client's "
              "copy before it reached the generator."),
        ("p", "I assembled and labelled the campaign-goal and tone corpus and "
              "implemented both classifiers as a controlled comparison — "
              "TF-IDF with logistic regression against Sentence-BERT "
              "embeddings with XGBoost. My most useful methodological "
              "contribution here was choosing the right test: with roughly a "
              "hundred test rows and two classifiers on one test set, only the "
              "disagreements carry information, so exact McNemar is correct "
              "where an accuracy comparison is not. The result — p = 1.000 for "
              "goal and p = 0.727 for tone — means the two approaches are "
              "statistically indistinguishable, and I argued in the report "
              "that choosing TF-IDF on cost and interpretability is a stronger "
              "claim than pretending it is more accurate. I also found and "
              "corrected the corpus filtering defect (D5) that had quartered "
              "the usable training data from 527 rows to 114."),
        ("p", "I implemented the platform-aware generation engine producing "
              "captions, hashtags, calls to action, image prompts and "
              "short-video briefs, and fixed the defect (D6) in which the "
              "`shorts` platform declared a video visual type but had no "
              "visual options defined, so the selector silently returned a "
              "static image brief."),
        ("p", "I designed and built **capability detection**, which I consider "
              "my strongest contribution. Reading a site to determine what it "
              "can actually do — sell, take subscriptions, capture leads, "
              "accept donations — stops the system recommending an action the "
              "client cannot perform. Evaluating it against hand labels on "
              "fifteen real websites taught me more than the accuracy figure "
              "did: two of the four initial disagreements were faults in my "
              "*labels*, not my detector, because a charity that sells "
              "merchandise has both donation and commerce and a publisher "
              "running a store has commerce as well as content. Modelling "
              "capabilities as independent flags rather than as a site "
              "category is what let the detector be right where the label was "
              "wrong. I also insisted the report state plainly that this "
              "sample is a development set and its figure is therefore fitted."),
        ("p", "Finally, I built the three-component scoring framework and the "
              "human-baseline harness. The most consequential piece of this "
              "work was negative: I discovered the engagement regressor had "
              "been trained with the outcome components from which its target "
              "was derived still among its features (D4). Adding a leakage "
              "guard moved R² from 0.9901 to −0.168. I then tested all eight "
              "text features for correlation with engagement under "
              "Holm–Bonferroni correction and found that none survives, "
              "establishing that the absence of signal is a property of the "
              "dataset rather than a modelling failure. I reduced the "
              "component's weight from 0.45 to 0.20 accordingly and made the "
              "model's own verdict visible in the interface rather than "
              "deleting the result. I also diagnosed the macOS OpenMP conflict "
              "between XGBoost and PyTorch that terminated training runs and "
              "API workers with no traceback."),

        ("h2", "A.2  215015D — Arqam Z. H."),
        ("h3", "Module 3 — Marketing Analytics and Decision Support"),
        ("p", "I was responsible for the analytics and decision-support "
              "module, which is the component through which the framework's "
              "feedback loop closes. I designed and implemented the pipeline "
              "described in Table 12: funnel construction and drop-off "
              "analysis disaggregated by stage, segment and policy; the "
              "journey-level feature builder; the conversion and drop-off "
              "models with bootstrap intervals against a stratified baseline; "
              "SHAP explanations; probability calibration; and the "
              "recommendation generator."),
        ("p", "I implemented four attribution models and, more importantly, "
              "the method for evaluating them. Because the simulator generates "
              "journeys from known per-channel influence, the true credit is "
              "available and each model can be scored by mean absolute error "
              "against it — a comparison observational data cannot support. On "
              "the imported audience, where no ground truth exists, I report "
              "**disagreement** instead of accuracy, which produced what I "
              "regard as the clearest single argument in the project against "
              "trusting one attribution model: across 7,811 converting "
              "journeys the widest pair disagrees over 68 % of all attributed "
              "credit. I also insisted on reporting that 20 % of those "
              "journeys have a single touchpoint, where the models agree by "
              "arithmetic rather than by evidence."),
        ("p", "The work I am most glad we did came from a question I could not "
              "answer at the interim review: whether ranking customers by "
              "predicted conversion is the right thing to rank by. It is not. "
              "A customer who would have converted anyway improves a response "
              "model's accuracy while contributing nothing to the campaign. "
              "Because uplift is identifiable only where assignment was "
              "randomised — and nothing in our own audience was randomised — I "
              "built the comparison on Hillstrom's randomised dataset, fitting "
              "S-learner and T-learner uplift models against the "
              "predicted-response policy the system was actually using. The "
              "two policies share only 56 % of their chosen customers at a "
              "30 % budget. I also wrote the caveat that matters: the Qini "
              "intervals overlap and the second uplift learner does *worse* "
              "than the current policy, so “use uplift modelling” is not a "
              "conclusion on its own."),
        ("p", "That finding created the next problem — no borrowed dataset can "
              "answer the question for *our* actions — and the answer is the "
              "contribution I would defend first. I designed the "
              "propensity-logged decision record: an append-only log holding "
              "every decision, the probability it was taken under, and what "
              "followed, with ten per cent of decisions randomised on purpose "
              "because a deterministic policy assigns probability zero to "
              "every action it does not take. I validated the estimators "
              "against a known answer in simulation and established the result "
              "I did not anticipate: without exploration the estimate is "
              "biased **upwards**, and the deterministic log looks *more* "
              "trustworthy by effective sample size — 1,094 against 107 — "
              "because every weight is 0 or 1. The standard diagnostic points "
              "the wrong way. I also measured what exploration costs "
              "(about 7.5 % of achievable reward at a 10 % rate) and showed "
              "that token exploration at 1 % is worse than none."),
        ("p", "Beyond my module I built the shared research infrastructure: "
              "the eleven-experiment runner, the statistics layer (percentile "
              "and paired bootstrap, Wilcoxon signed-rank, exact McNemar, "
              "Wilson intervals, Cliff's delta), the figure generator that "
              "draws every chart from the experiment tables, and the chapter "
              "generator that authors the evaluation prose once and "
              "interpolates the measured values — so that no number in "
              "Chapter 7 is copied by hand and no figure can disagree with the "
              "value it plots. I found and fixed a reproducibility defect (D7) "
              "in which iterating an unordered set made a reported R² depend "
              "on the process hash seed. I contributed the shared database "
              "schema, the analytics and decision routes, the dashboard's "
              "analytics page, and the principle that provenance must be "
              "derived at write time rather than asserted by the caller. I "
              "compiled and wrote this report."),

        ("h2", "A.3  215110N — Sarah M. M. F."),
        ("h3", "Module 1 — Audience Targeting and Personalization"),
        ("p", "I was responsible for the hybrid segmentation engine, the first "
              "module in the pipeline and the source of the segment taxonomy "
              "every other module consumes. I prepared and preprocessed the "
              "8,000-customer dataset — missing-value handling, categorical "
              "encoding, feature scaling and the derived behavioural features "
              "— and established the five-segment taxonomy shared across the "
              "system."),
        ("p", "I implemented all three methods as peers over a common feature "
              "matrix: a rule-based segmenter, k-means, and Ward-linkage "
              "agglomerative clustering. I then designed the agreement vote "
              "that combines them and produces the calibrated confidence, and "
              "— at my supervisors' prompting — ran the ablation that compares "
              "the hybrid against each of its own components on the same "
              "customers."),
        ("p", "That ablation produced the result I found hardest to accept and "
              "am now most convinced was worth reporting. **The hybrid does "
              "not separate conversion better than the rules alone** — 0.3838 "
              "against 0.3837, a difference well inside the bootstrap "
              "interval. Clustering on its own reaches 0.0343. My first "
              "instinct was to look for a better metric; the right response "
              "was to report the number and re-examine what the hybrid is "
              "actually for. It earns its place by producing a confidence "
              "calibrated from three-way agreement and by making cold start "
              "explicit — not by separating conversion further. I also report "
              "the silhouette of 0.087 and the fact that all three methods "
              "disagree for 35 % of customers, because a study quoting only "
              "the separation would hide how heavily the clusters overlap."),
        ("p", "I found and corrected two defects in my own module. The first "
              "(D1) was that the confidence classifier had been trained with "
              "the rule label among its inputs while the target was the hybrid "
              "consensus, so it was largely reading off its own answer. "
              "Reproducing both versions on the same split showed something I "
              "did not expect: accuracy barely moved, from 0.9213 to 0.9200, "
              "while the number of customers emerging at confidence 1.00 fell "
              "from 450 to 3. Accuracy is not what the leak corrupts — the "
              "confidence attached to every downstream decision is — and that "
              "is exactly why it survived review with every test green."),
        ("p", "The second (D2) was more serious. My agreement vote tested "
              "whether the two clusterings agreed *before* it tested whether "
              "the rules had identified a cold-start customer. Clustering "
              "cannot represent “there is not enough evidence about this "
              "person”; it must place everyone somewhere. So whenever the two "
              "clusterings happened to agree, they overruled the rules. Of the "
              "163 cold-start customers the rules detect, that ordering kept "
              "127 — and on the live audience the segment went to zero. My "
              "module's novel contribution was being erased by its own "
              "pipeline. I reordered the vote so cold start is resolved "
              "immediately after unanimity and added a regression test. The "
              "general principle I would defend in a viva is that **a method "
              "that cannot represent a finding does not get a vote on it.**"),
        ("p", "I also replaced hardcoded cluster-index naming (D3) with names "
              "derived from centroids at run time, implemented the "
              "minimum-audience rule under which the engine declines to "
              "cluster and states why, and built the second feature domain so "
              "that live tracked visitors are segmented on page views, scroll "
              "depth and session features rather than on email history a "
              "first-time visitor does not have. I wrote the Module 1 sections "
              "of this report."),

        ("h2", "A.4  215129F — Zanar M. H. M. R. A."),
        ("h3", "Module 2 — Marketing Automation and Campaign Management"),
        ("p", "I was responsible for the campaign automation module, which "
              "consumes segments from Module 1 and produces the interaction "
              "log Module 3 analyses. I designed it as a controlled experiment "
              "rather than as a single implementation: the policy engine is "
              "the only component that differs between the three arms, while "
              "the profile builder, response model, message templates, "
              "response simulator and evaluator are shared, so that any "
              "measured difference is attributable to the policy alone."),
        ("p", "I implemented all three policies — fixed workflow, "
              "trigger-based and hybrid — behind a common interface, together "
              "with the message template library and the response simulation "
              "layer, whose per-segment propensities I calibrated against the "
              "dataset's own conversion rates. During early integration I "
              "built a mock segmentation file with the agreed schema so my "
              "module could be developed in parallel with Module 1 and later "
              "swapped to the real output without changing the automation "
              "logic."),
        ("p", "I made two methodological decisions I would defend. The first "
              "was the metric: **conversions per thousand sends**, not "
              "per-customer conversion rate. A per-user rate rises simply by "
              "sending more messages, which would hand the win to the fixed "
              "workflow for sending most rather than for sending best — and "
              "the message volumes differ sharply (4.00 messages per customer "
              "for fixed against 1.32 for trigger). I report both, so the "
              "choice of metric is visible to the reader rather than decisive "
              "in the background. The second was the experimental design: "
              "thirty independent seeds, each putting the same 8,000 customers "
              "through all three policies, which makes the comparison paired "
              "and means paired tests and effect sizes are the correct "
              "analysis."),
        ("p", "I also fitted a stratified dummy classifier alongside the real "
              "response models and published it in the same table, because the "
              "dataset's base rate is high enough that a model can look "
              "accurate by predicting the majority class for everyone. And I "
              "designed the operational complexity measure — the count of "
              "distinct decision rules and branch points each policy requires "
              "— because effectiveness alone is not a sufficient basis for an "
              "engineering choice. The trigger policy leads the fixed workflow "
              "by 3.3 conversions per thousand sends for three extra rules, "
              "which is the trade the report argues explicitly rather than "
              "assumes."),
        ("p", "The finding I did not expect is the one I insisted we keep. "
              "When the same three policies were run against the imported "
              "audience in the live system, the ranking **changed**: the "
              "simulator favours trigger, the live build favours hybrid. Both "
              "measurements are volume-controlled, so the difference lies in "
              "how response is modelled — segment-level propensities against "
              "per-customer rates drawn from each customer's own recorded "
              "email history. Neither is an observation of real people "
              "reacting. Quoting whichever run supported the conclusion we "
              "preferred would have been the one genuinely dishonest option "
              "available to us, so the report presents the instability itself "
              "as the result. I also contributed the campaign execution and "
              "action-plan routes, the tracked-link mechanism, and the "
              "campaigns page of the dashboard."),

        # ============================================== APPENDIX B
        ("h1", "APPENDIX B — ADDITIONAL IMPLEMENTATION DETAILS"),

        ("h2", "B.1 Reproducing the System and the Results"),
        ("p", "The system and every number in Chapter 7 are reproducible from "
              "a clean checkout. The following commands provision "
              "dependencies, start the database and services, serve the "
              "demonstration store, import the research audience and "
              "regenerate the entire evaluation."),
        ("code",
         "make setup      # once — Python, Node, browser, environment file\n"
         "make db         # PostgreSQL 16 — Homebrew service, else Docker\n"
         "make db-create  # once, on the Homebrew path — role and database\n"
         "\n"
         "make api        # FastAPI backend          (terminal 2)\n"
         "make web        # Next.js dashboard        (terminal 3)\n"
         "make site       # demonstration store      (terminal 4)\n"
         "\n"
         "make demo       # import 8,000 customers, run every module\n"
         "make research   # run all 11 experiments, redraw every figure,\n"
         "                # regenerate Chapter 7\n"
         "make test       # the full test suite"),
        ("table", {"caption": f"{T(1)} — Service endpoints in the running "
                              "system.",
                   "header": ["Service", "Address", "Purpose"],
                   "rows": [
                       ["Dashboard", "http://localhost:3000",
                        "Marketer interface — 7 pages plus authentication"],
                       ["Demonstration store", "http://localhost:4000",
                        "The e-commerce site under study, with mos.js "
                        "installed"],
                       ["API", "http://localhost:8000", "FastAPI service"],
                       ["API documentation", "http://localhost:8000/docs",
                        "Interactive OpenAPI documentation"],
                       ["PostgreSQL", "localhost:5434",
                        "Database on a non-default port to avoid collisions"],
                   ]}),

        ("h2", "B.2 Repository Structure"),
        ("code",
         "web/              Next.js dashboard (7 pages + auth + onboarding)\n"
         "api/              FastAPI backend\n"
         "  routers/        sites, segments, campaigns, analytics, content,\n"
         "                  actions, decisions, tracking, auth\n"
         "  services/       module wrappers, decision log, provenance\n"
         "  static/mos.js   first-party tracking snippet\n"
         "  schema.sql      database schema\n"
         "modules/\n"
         "  m1_segmentation/  segment.py — the hybrid engine\n"
         "  m2_automation/    policy engine, simulator, evaluation\n"
         "  m3_analytics/     funnel, attribution, prediction, recommender\n"
         "research/\n"
         "  experiments/    E1 … E11\n"
         "  stats.py        bootstrap, Wilcoxon, McNemar, Wilson, Cliff's d\n"
         "  figures.py      every figure in Chapter 7\n"
         "  chapters.py     the prose, authored once\n"
         "  results/        results.json and every experiment table\n"
         "demo-site/        the e-commerce store under study\n"
         "scripts/          setup, dataset import, model training\n"
         "tests/            the platform test suite\n"
         "report/\n"
         "  build/          the .docx builder and chapter content\n"
         "  assets/         architecture figures and screenshots"),

        ("h2", "B.3 The Experiment Catalogue"),
        ("p", "Each experiment is independently runnable and writes its own "
              "tables to `research/results/`. The complete catalogue is listed "
              "below; the results themselves are in Chapter 7."),
        ("table", {"caption": f"{T(2)} — The eleven experiments and the data "
                              "each uses.",
                   "header": ["ID", "Question", "Data", "Primary metric"],
                   "rows": [
                       ["E1", "Does the hybrid beat its own components?",
                        "8,000-customer dataset",
                        "Conversion separation, silhouette"],
                       ["E2", "The two Module 1 defects, reproduced",
                        "8,000-customer dataset",
                        "Segment survival, accuracy, certainty"],
                       ["E3", "Which automation policy wins, and at what "
                              "cost?",
                        "Module 2 simulator, 30 paired seeds + live build",
                        "Conversions per 1,000 sends"],
                       ["E4", "Do the attribution models agree?",
                        "Module 3 simulator + 7,811 live journeys",
                        "MAE vs ground truth; pairwise disagreement"],
                       ["E5", "Prediction quality, and its transfer",
                        "Module 3 features + imported audience",
                        "ROC-AUC against a stratified baseline"],
                       ["E6", "TF-IDF versus Sentence-BERT",
                        "527-row goal/tone corpus",
                        "Macro-F1, exact McNemar"],
                       ["E7", "Engagement leakage and text signal",
                        "12,000-row engagement corpus",
                        "R², Spearman, Holm–Bonferroni"],
                       ["E8", "Targeting by uplift versus by predicted "
                              "response",
                        "Hillstrom, 64,000 randomised",
                        "Qini, incremental response"],
                       ["E9", "Does the decision log make the policy "
                              "learnable?",
                        "Simulated world with known rewards",
                        "Estimator bias, RMSE, effective sample size"],
                       ["E10", "Can the system read what a website can do?",
                        "15 real websites, hand-labelled",
                        "Agreement, precision, recall (Wilson)"],
                       ["E11", "What a per-website action set costs in data",
                        "Simulated world with known rewards",
                        "RMSE, logged decisions required"],
                   ]}),

        ("h2", "B.4 Statistical Methods"),
        ("p", "Every interval and every test in Chapter 7 comes from "
              "`research/stats.py`. Each method was chosen because it makes "
              "the fewest assumptions the data can violate."),
        ("table", {"caption": f"{T(3)} — Statistical methods, and why each "
                              "was chosen.",
                   "header": ["Method", "Applied to", "Why this one"],
                   "rows": [
                       ["Percentile bootstrap, 10,000 resamples [52]",
                        "Separation, silhouette, macro-F1, MAE, Qini",
                        "These are not means and have no closed-form standard "
                        "error; resampling makes no distributional claim"],
                       ["Paired bootstrap and Wilcoxon signed-rank [65]",
                        "The three-policy comparison over 30 seeds",
                        "The same customers pass through every policy, so the "
                        "runs are paired; ignoring that overstates the p-value"],
                       ["Exact McNemar [30]",
                        "TF-IDF against Sentence-BERT",
                        "Two classifiers on one test set: only the "
                        "disagreements carry information, and the exact "
                        "binomial is correct at this sample size"],
                       ["Cliff's delta [34]",
                        "Every paired policy comparison",
                        "With thirty seeds almost any difference is "
                        "significant; the effect size says whether it matters"],
                       ["Wilson score interval [64]",
                        "Capability-detection agreement",
                        "Correct near a proportion of 1.0, where the normal "
                        "approximation produces impossible bounds"],
                       ["Holm–Bonferroni correction [20]",
                        "The eight engagement text features",
                        "Testing eight features without correction would "
                        "manufacture a significant one by chance"],
                   ]}),

        ("h2", "B.5 Reproducibility Guarantees"),
        ("bullets", [
            "**Seeded.** All randomness derives from seed 42. The importer is "
            "deterministic given the source CSV and idempotent on re-run.",
            "**Verified against source.** Import fidelity is asserted after "
            "every run: sessions, page views, time on site, clicks and "
            "purchases match the source CSV exactly.",
            "**Hash-seed independent.** A subprocess test varies "
            "PYTHONHASHSEED and asserts the engagement result is unchanged, "
            "after defect D7 showed set iteration could alter it.",
            "**Generated, not transcribed.** Every figure in Chapter 7 is "
            "drawn from the experiment tables and the chapter itself is "
            "rendered from `results.json`, so no value in the report is "
            "typed by hand.",
            "**Verified from empty.** The full pipeline has been run from an "
            "empty database to a finished report, so the reproduction path is "
            "known to work and not merely intended to.",
        ]),

        ("h2", "B.6 Replacing the Screenshot Placeholders"),
        ("p", "Figures 10 through 29 are placeholders showing what each "
              "capture should contain. To insert the real screenshots, save "
              "each capture over the file of the same name in "
              "`report/assets/placeholders/` and rebuild the report with "
              "`python3 report/build/report_build.py`. Nothing else changes — "
              "the captions, numbering and List of Figures are unaffected."),
    ]


BLOCKS = _build(_FIG0, _TAB0)


def set_label_offsets(fig_last, tab_last):
    """Renumber the appendix labels to continue after the generated chapter."""
    global BLOCKS, _FIG0, _TAB0
    _FIG0, _TAB0 = fig_last, tab_last
    BLOCKS = _build(fig_last, tab_last)
    return BLOCKS
